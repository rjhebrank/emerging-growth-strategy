# T4: Build Pre-Loaded Bloomberg Excel Templates (Batched)

**Status:** PENDING
**Assigned to:** Terminal 2
**Created:** 2026-02-27

---

## Objective

Build a SET of Excel workbooks with Bloomberg formulas pre-loaded, split into phases to avoid hitting Bloomberg's request limits. Each workbook is a manageable batch that won't timeout.

**Problem:** Bloomberg Excel Add-in chokes on 9,000+ simultaneous requests. BDH (historical) calls are especially heavy. Must batch into groups of 50-100 tickers.

**Output:**
```
templates/
├── Phase1_Universe_Screen.xlsx      # ~8,000 BDP calls (lightweight, runs in one shot)
├── Phase2_Price_Batch_01.xlsx       # Tickers 1-50 price history (50 BDH calls)
├── Phase2_Price_Batch_02.xlsx       # Tickers 51-100
├── Phase2_Price_Batch_03.xlsx       # Tickers 101-150
├── Phase2_Price_Batch_04.xlsx       # Tickers 151-200
├── Phase2_Price_Batch_05.xlsx       # Tickers 201-250
├── Phase2_Price_Batch_06.xlsx       # Tickers 251-300
├── Phase2_Price_Batch_07.xlsx       # Tickers 301-350
├── Phase2_Price_Batch_08.xlsx       # Tickers 351-400
├── Phase3_Fundamentals_Batch_01.xlsx  # Tickers 1-100 EPS+Revenue (200 BDH calls)
├── Phase3_Fundamentals_Batch_02.xlsx  # Tickers 101-200
├── Phase3_Fundamentals_Batch_03.xlsx  # Tickers 201-300
├── Phase3_Fundamentals_Batch_04.xlsx  # Tickers 301-400
├── Phase4_Scoring.xlsx              # Factor scores + composite + signals (BDP only, light)
└── README_Instructions.xlsx         # Step-by-step workflow
```

**User workflow on Bloomberg machine:**
1. Open Phase1 → Ctrl+Shift+R → wait 5-10 min → save → copy qualifying tickers
2. Paste tickers into Phase2 batches → refresh each one (2-3 min each) → save as values
3. Paste tickers into Phase3 batches → refresh each (1-2 min each) → save as values
4. Combine all saved data into Phase4 → refresh for sector data → signals generated
5. Export final Phase4 as the file the Python engine reads

Each batch stays well under Bloomberg's limits.

---

## Reference Doc

Read `docs/06-bloomberg-data-pull.md` for the exact formulas and template layout. That doc is the source of truth.

---

## What to Build

Use `openpyxl` to create an Excel workbook with 5 sheets. Every cell that needs a Bloomberg formula gets the formula as a STRING (Bloomberg will evaluate it when opened on a terminal machine). openpyxl won't execute them — it just writes the formula text into the cell.

### Sheet 1: "Universe"

**Row 1 = Headers (bold, frozen pane):**
A1: "Ticker" | B1: "Market Cap ($M)" | C1: "Exchange" | D1: "Avg Vol (20d)" | E1: "Price" | F1: "Dollar Volume" | G1: "MktCap Pass" | H1: "Exchange Pass" | I1: "DolVol Pass" | J1: "Price Pass" | K1: "ALL PASS"

**Row 2 = Formulas:**
- A2: `=BDS("RTY Index","INDX_MEMBERS")` — this spills ~2,000 tickers down column A
- B2: `=BDP(A2&" US Equity","CUR_MKT_CAP")`
- C2: `=BDP(A2&" US Equity","EXCH_CODE")`
- D2: `=BDP(A2&" US Equity","VOLUME_AVG_20D")`
- E2: `=BDP(A2&" US Equity","PX_LAST")`
- F2: `=D2*E2`
- G2: `=AND(B2>=50,B2<=10000)`
- H2: `=OR(C2="NAS",C2="NYS",C2="ASE")`
- I2: `=F2>=500000`
- J2: `=E2>=2`
- K2: `=AND(G2,H2,I2,J2)`

**Rows 3-2501:** Copy B2:K2 formulas down for 2,500 rows (to cover full Russell 2000 spill). Each row references its own row's A column (A3, A4, etc.). The BDS in A2 will spill tickers into A3, A4, etc. automatically.

**Formatting:**
- Header row: bold, light gray background, border
- Freeze panes at row 2
- Column widths: A=12, B=15, C=10, D=15, E=10, F=15, G-K=12
- Conditional formatting on K column: TRUE = green fill, FALSE = red fill

### Sheet 2: "Price History"

**Instructions cell A1:** "INSTRUCTIONS: After Universe sheet populates, copy qualifying tickers (K=TRUE) into column A below starting at A3. Each ticker's BDH will spill ~315 rows of OHLCV data. Tickers are spaced 320 rows apart."

**Row 2 = Headers:**
A2: "Ticker" | B2: "Date" | C2: "Open" | D2: "High" | E2: "Low" | F2: "Close" | G2: "Volume"

**Pre-built formula blocks for up to 100 tickers** (can handle more but 100 is a good starting batch):
- Row 3: A3 left blank (user pastes ticker), B3 gets the BDH formula:
  `=BDH(A3&" US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME",TEXT(EDATE(TODAY(),-15),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days","A","Fill","P","CshAdjNormal","Y","CshAdjAbnormal","Y")`
- Row 323: A323 blank (next ticker), B323 gets same BDH formula referencing A323
- Row 643: A643 blank, B643 same pattern
- Continue every 320 rows for 100 blocks (last block at row 3 + 99*320 = row 31683)

**BUT ALSO** add a helper approach: Create a "Ticker List" section in column I:
- I1: "Paste qualifying tickers here (one per row)"
- I2: "Then run the VBA macro or manually copy to column A at 320-row intervals"

**Actually, better approach:** Since manually pasting tickers every 320 rows is tedious, create a simpler layout:
- Column A rows 3, 323, 643, 963... = formulas that reference a ticker list
- Add a "Ticker Input" column (column I) where user pastes all qualifying tickers contiguously (I3, I4, I5...)
- A3: `=I3`, A323: `=I4`, A643: `=I5`, etc. — maps contiguous ticker list to spaced-out BDH blocks automatically

This way the user just pastes their filtered ticker list into column I and everything chains through.

### Sheet 3: "Fundamentals"

**Row 1 = Headers:**
A1: "Ticker" | B1: "EPS Date" | C1: "EPS" | D1: (empty) | E1: (empty) | F1: (empty) | G1: (empty) | H1: (empty) | I1: (empty) | J1: "Rev Date" | K1: "Revenue"

**Row 2 instructions:** "Each ticker block = 10 rows. BDH returns up to 8 quarterly data points."

**Pre-built blocks for 100 tickers, spaced 10 rows apart:**
- Row 3: A3 blank (or linked from ticker list), B3: `=BDH(A3&" US Equity","IS_DILUTED_EPS",TEXT(EDATE(TODAY(),-24),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Per","Q","Days","A","Fill","P")`
- J3: `=BDH(A3&" US Equity","SALES_REV_TURN",TEXT(EDATE(TODAY(),-24),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Per","Q","Days","A","Fill","P")`
- Row 13: next ticker block (A13, B13, J13)
- Row 23: next, etc.

**Same ticker input helper:** Column M for contiguous ticker list:
- M1: "Paste qualifying tickers here"
- A3: `=M3`, A13: `=M4`, A23: `=M5`, etc.

**YoY Growth calculations pre-built in each block:**
- Column L (EPS YoY Growth): In each ticker's block, at the block's start row:
  `=IF(C7=0,IF(C3>0,999,0),(C3-C7)/ABS(C7)*100)`
  (C3 = most recent quarter, C7 = same quarter last year, 4 rows apart)
- Column N (Rev YoY Growth):
  `=IF(K7<=0,IF(K3>0,999,0),(K3-K7)/K7*100)`

### Sheet 4: "Factor Scores"

**Row 1 = Headers:**
A1: "Ticker" | B1: "6-Mo Return (%)" | C1: "RS Percentile" | D1: "EPS Growth YoY" | E1: "EPS Growth (capped)" | F1: "Rev Growth YoY" | G1: "Rev Growth (capped)" | H1: "Price vs 52-Wk High (%)" | I1: "Quality: EPS>=5%" | J1: "Quality: Rev>=5%" | K1: "Quality: Price>=75%" | L1: "ALL QUALITY PASS"

**Row 2+ formulas (for up to 2,500 tickers):**
- A2: linked from Universe ticker list (only qualifying tickers)
- B2: `=(close_today - close_126d_ago) / close_126d_ago * 100` — NOTE: This can't easily reference Price History sheet due to the block layout. Instead, put a note: "Populate from Python engine or manually from Price History sheet"
- C2: `=PERCENTRANK.INC($B$2:$B$2500,B2)*100`
- D2: linked from Fundamentals sheet L column (EPS YoY growth)
- E2: `=MIN(D2,100)`
- F2: linked from Fundamentals sheet N column (Rev YoY growth)
- G2: `=MIN(F2,100)`
- H2: `=Universe!E2/BDP(A2&" US Equity","HIGH_52WEEK")*100` — or reference a 52-week high column
- I2: `=D2>=5`
- J2: `=F2>=5`
- K2: `=H2>=75`
- L2: `=AND(I2,J2,K2)`

### Sheet 5: "Portfolio"

**Row 1 = Headers:**
A1: "Ticker" | B1: "Composite Score" | C1: "Rank" | D1: "In Top 25" | E1: "Prior Month Rank" | F1: "Signal" | G1: "Target Weight (%)" | H1: "Sector"

**Row 2+ formulas:**
- B2: `=0.40*'Factor Scores'!C2 + 0.20*'Factor Scores'!E2 + 0.20*'Factor Scores'!G2 + 0.20*'Factor Scores'!H2`
- C2: `=RANK(B2,$B$2:$B$2500,0)`
- D2: `=C2<=25`
- E2: *(manual — paste from prior month)*
- F2: `=IF(AND(D2=TRUE,E2=""),"BUY",IF(AND(D2=FALSE,E2<>""),"SELL",IF(AND(D2=TRUE,E2<>""),"HOLD","")))`
- G2: `=IF(D2,4,0)`
- H2: `=BDP(A2&" US Equity","GICS_SECTOR_NAME")` — sector for concentration monitoring

**Drag all formulas down to row 2501.**

---

## Additional Requirements

### Formatting
- All sheets: professional look, consistent fonts (Calibri 11), gridlines
- Header rows: bold, dark blue background (#1B2A4A), white text, frozen
- Number formats: Market cap = #,##0, Price = #,##0.00, Percentages = 0.00%, Volume = #,##0
- Column auto-width or sensible fixed widths
- Tab colors: Universe=blue, Price History=green, Fundamentals=orange, Factor Scores=purple, Portfolio=red

### Helper Notes
- Add a "README" sheet (Sheet 0) with:
  - Step-by-step instructions for first-time setup
  - Monthly refresh workflow
  - Troubleshooting tips for #N/A and #NAME? errors
  - Link to docs/06-bloomberg-data-pull.md for full reference
  - Date: auto-populated with TODAY()

### File Location
Save to: `templates/bloomberg_template.xlsx`

---

## Technical Notes for the Agent

- Use `openpyxl` to build the workbook
- Bloomberg formulas are just strings — write them with `cell.value = '=BDP(...)'`
- openpyxl will save them as formula strings; Bloomberg evaluates when opened on a terminal machine
- Use `openpyxl.styles` for formatting (Font, PatternFill, Border, Alignment)
- Use `openpyxl.worksheet.datavalidation` if helpful
- Use `openpyxl.utils` for column width helpers
- Test that the file opens cleanly in regular Excel (formulas will show #NAME? without Bloomberg — that's expected and correct)

---

## Instructions for Terminal 2

**CRITICAL: Deploy MULTIPLE agents in parallel. Do NOT put one agent on the whole task.**

1. Read this task + `docs/06-bloomberg-data-pull.md`
2. Deploy agents in parallel — suggested split:
   - **Agent 1:** Build Phase1_Universe_Screen.xlsx + README_Instructions.xlsx
   - **Agent 2:** Build all 8 Phase2_Price_Batch files (loop in one agent is fine since they're identical structure with different row offsets)
   - **Agent 3:** Build all 4 Phase3_Fundamentals_Batch files
   - **Agent 4:** Build Phase4_Scoring.xlsx (factor scores + composite + signals)
   - **Agent 5:** Build a `templates/combine_batches.py` helper script that merges all the saved Phase2+Phase3 data into a single clean Excel file the Python engine can read
3. Review all outputs — verify each .xlsx opens without corruption
4. Mark task DONE when complete
