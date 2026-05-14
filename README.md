# BoardBudget

BoardBudget is a small local planning tool for allocating people to project activities based on estimated hours.

One board is one `.xlsx` file. The Excel file is both the app storage format and the export format, so boards stay easy to inspect, copy, send, archive, and edit outside the app when needed.

BoardBudget is intentionally simple:

- no database
- no login
- no cloud sync
- no API layer
- Python performs the planning and economic calculations
- Excel stores input and generated output sheets

## Installation

Use Python 3.11 or newer.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Run

```bash
streamlit run boardbudget/app.py
```

The app stores boards in the local `boards/` folder.

## Create And Edit A Board

From the sidebar you can create a new board, create the Pitagora sample board, open an existing `.xlsx` board, duplicate the selected board, recalculate generated sheets, and download the current board. The download button prepares a fresh Excel export by recalculating generated sheets before serving the file.

BoardBudget uses editable tables with explicit save buttons. It does not autosave on every cell edit.

Use the tabs to edit:

- `People`: `person_id`, `name`, `hours_per_day`, `active`
- People also include `daily_cost`, the delivery cost for one 8-hour person-day.
- `Activities`: `activity_id`, `order`, `name`, `estimated_days`, `estimated_hours`, `max_hours_per_day`, `daily_price`, `status`, `notes`, `price_notes`
- `Assignments`: one row per planned activity with multiselect people tags
- `Absences`: calendar matrix with empty, `? 4`, `? 8`, `X 4`, and `X 8`

The advanced assignment expander still exposes the normalized raw table. Excel also stores assignments as normalized rows: `activity_id`, `person_id`.

After changing inputs, click the relevant save button. Then use **Recalculate current board** in the sidebar to regenerate calendar, dashboard, warnings, and economics sheets.

The sidebar also includes **⚙️ Settings**:

- font size scale: Small, Normal, Large
- theme preference: System/default, Light, Dark
- non-working day color for weekend and holiday rows
- absence day color for confirmed person-specific absences

Settings are kept local in `boardbudget_settings.json` when saved.

## Estimated Effort

`estimated_hours` is canonical and is what the planner uses. `estimated_days` is a convenience field based on 8 hours per day.

Rules:

- If `estimated_hours` is filled and `estimated_days` is blank, days are calculated as `estimated_hours / 8`.
- If `estimated_days` is filled and `estimated_hours` is blank, hours are calculated as `estimated_days * 8`.
- If both are filled, `estimated_hours` wins.
- Simple arithmetic expressions are supported, such as `20*8`, `5*8`, `2.5*8`, and `10/2`.

## Economic Dashboard

Activities can include `daily_price`, the selling or revenue price for 1 person-day / 8 hours.

People can include `daily_cost`, the delivery cost for 1 person-day / 8 hours.

```text
estimated_value = estimated_hours / 8 * daily_price
allocated_value = allocated_hours / 8 * daily_price
delivery_cost = allocated_hours / 8 * person.daily_cost
expected_margin = total_estimated_value - estimated_delivery_cost
```

The Dashboard tab keeps the primary economic cards small:

- Activity Value: value of PLANNED and DONE activities
- Forecast Delivery Cost: scheduled allocation cost from people daily costs
- Delivered Cost To Date: scheduled allocation cost through today

Secondary cards show Theoretical Saving If Finished Today and Forecast Margin. The theoretical saving is `Activity Value - Delivered Cost To Date`.

Activity Economics includes PLANNED and DONE activities. DONE activities are considered acquired value/revenue. CANCELLED activities are excluded from economic value by default.

## Calendar Behavior

Planning allocates only on working days. Saturdays, Sundays, and Italian public holidays are non-working days and receive no allocations.

The visible calendar includes every calendar date between the planned start and planned end, including weekends and Italian public holidays. Weekend and holiday rows use a soft configurable highlight color. The calendar uses a sortable, resizable grid view, with date/day columns pinned and person columns made wider for activity chunks such as `1 Supporto GOSP 2026 4h + 2 Assessment fase 2 4h`.

The raw allocation sheet does not include fake weekend or holiday allocation rows.

## Vacations And Absences

The Absences tab stores person-specific absences in `04_Absences`.

Cell values:

- empty: no absence
- `? 4`: tentative 4-hour absence, no planning effect
- `? 8`: tentative 8-hour absence, no planning effect
- `X 4`: confirmed 4-hour absence, reduces that person's capacity by 4 hours
- `X 8`: confirmed full-day absence, that person has 0 capacity that date

Only confirmed `X` absences affect planning. Tentative `?` absences are informational. Absence hours do not create delivery cost; costs are calculated only from generated allocations.

The Board Calendar shows confirmed absences inside the affected person's cell and highlights that cell with the configured absence color. Weekend and Italian holiday rows remain global non-working rows highlighted with the non-working color.

## Excel Sheet Format

Every board workbook contains these input sheets:

- `01_Board`
- `02_People`
- `03_Activities`
- `04_Assignments`
- `04_Absences`

The final `03_Activities` column order is:

```text
activity_id, order, name, estimated_days, estimated_hours,
max_hours_per_day, daily_price, status, notes, price_notes
```

The app replaces these generated sheets when recalculating:

- `05_Calendar`
- `06_Dashboard`
- `07_Warnings`
- `08_Activity_Economics`
- `09_Board_Calendar`
- `10_Person_Economics`

Existing older boards remain loadable. Missing v2/v3 columns are defaulted safely and written the next time the board is saved.

## Planning Rules

- Planning is in hours.
- Default capacity is 8 hours per person per day.
- Working days are Monday to Friday, excluding Italian public holidays.
- Confirmed vacations/absences reduce person-specific daily capacity.
- Activity `order` is a priority, not a global dependency.
- Shared activities are independent per person.
- Shared activity hours are no longer split equally. A shared activity has one global remaining-hours bucket, and assigned active people greedily consume it until the activity is complete.
- Each person is filled up to daily capacity when possible.
- `max_hours_per_day` limits each assigned person on that activity for that date.
- A person can work on multiple activities in the same day.
- `DONE` and `CANCELLED` activities are skipped.
- DONE activities are skipped by the planner but included in economics as acquired value.
- Activities without assignments or invalid estimated hours produce warnings.
- Planning is deterministic: activities sort by `order`, then `activity_id`.
- Planning stops after a safe maximum of 730 calendar days and reports an error if work remains.

## Table Usability

Display tables use AgGrid where practical, with user-resizable columns, sortable headers, and horizontal scrolling. Date/day columns and person columns are visually emphasized in the calendar. Sorting is UI-only and does not rewrite Excel. Editing tables remain lightweight Streamlit editors with configured column widths.

## Known Limitations

- No manual timesheet or actual-hours tracking yet.
- Actual completion is still manually/perceptually determined; there is no automatic "finished" signal.
- No detailed timesheet-based cost accounting yet; delivery cost is planned from calendar allocations and person daily cost.
- Absences are simple capacity reductions; there is no approval workflow.
- Tentative absences are informational only.
- No holiday calendar configuration beyond Italy.
- Input editors stay lightweight where AgGrid editing would add too much complexity.
- Dynamic full theme switching depends on Streamlit limitations; BoardBudget applies a lightweight app-level CSS preference.
- No authentication, multi-user coordination, database, or cloud sync.

## Future Ideas

- Import people and activities from an existing workbook.
- Optional holiday calendars.
- Optional per-person availability windows.
- Actual hours tracking.
- Simple charts in the dashboard tab.
- More Excel formatting for generated sheets.
