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

From the sidebar you can create a new board, create the Pitagora sample board, open an existing `.xlsx` board, duplicate the selected board, recalculate generated sheets, and download the current board.

BoardBudget uses editable tables with explicit save buttons. It does not autosave on every cell edit.

Use the tabs to edit:

- `People`: `person_id`, `name`, `hours_per_day`, `active`
- `Activities`: `activity_id`, `order`, `name`, `estimated_days`, `estimated_hours`, `max_hours_per_day`, `daily_price`, `status`, `notes`, `price_notes`
- `Assignments`: one row per planned activity with multiselect people tags

The advanced assignment expander still exposes the normalized raw table. Excel also stores assignments as normalized rows: `activity_id`, `person_id`.

After changing inputs, click the relevant save button. Then use **Recalculate current board** in the sidebar to regenerate calendar, dashboard, warnings, and economics sheets.

## Estimated Effort

`estimated_hours` is canonical and is what the planner uses. `estimated_days` is a convenience field based on 8 hours per day.

Rules:

- If `estimated_hours` is filled and `estimated_days` is blank, days are calculated as `estimated_hours / 8`.
- If `estimated_days` is filled and `estimated_hours` is blank, hours are calculated as `estimated_days * 8`.
- If both are filled, `estimated_hours` wins.
- Simple arithmetic expressions are supported, such as `20*8`, `5*8`, `2.5*8`, and `10/2`.

## Economic Dashboard

Activities can include `daily_price`, the selling price for 1 person-day / 8 hours.

```text
estimated_value = estimated_hours / 8 * daily_price
allocated_value = allocated_hours / 8 * daily_price
```

The Dashboard tab shows total estimated value, total allocated value, remaining allocated value from today, and an activity economics table.

## Calendar Behavior

Planning still allocates work Monday to Friday only.

The visible calendar includes every calendar date between the planned start and planned end, including Saturdays, Sundays, and Italian public holidays. Weekend and holiday rows are shown in light red in the Streamlit calendar view. Holidays are visual only in v2; they are not capacity blockers beyond the existing Monday-Friday planning rule.

The raw allocation sheet does not include fake weekend or holiday allocation rows.

## Excel Sheet Format

Every board workbook contains these input sheets:

- `01_Board`
- `02_People`
- `03_Activities`
- `04_Assignments`

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

Existing older boards remain loadable. Missing v2 columns are defaulted safely and written the next time the board is saved.

## Planning Rules

- Planning is in hours.
- Default capacity is 8 hours per person per day.
- Working days are Monday to Friday.
- Holidays, vacations, sick leave, and part-time exceptions are ignored for allocation in v2.
- Activity `order` is a priority, not a global dependency.
- Shared activities are independent per person.
- If an activity is assigned to multiple people, estimated hours are split equally.
- Each person is filled up to daily capacity when possible.
- `max_hours_per_day` limits each assigned person on that activity for that date.
- A person can work on multiple activities in the same day.
- `DONE` and `CANCELLED` activities are skipped.
- Activities without assignments or invalid estimated hours produce warnings.
- Planning is deterministic: activities sort by `order`, then `activity_id`.
- Planning stops after a safe maximum of 730 calendar days and reports an error if work remains.

## Table Usability

Column widths are configured for readability. Fully persistent manual column resizing depends on Streamlit table capabilities.

## Known v2 Limitations

- Italian holidays are visual only; they do not change capacity.
- No manual timesheet or actual-hours tracking yet.
- No costs different from selling prices yet.
- No holiday calendar configuration beyond Italy.
- No persistent manual column resizing beyond Streamlit column configuration.
- No authentication, multi-user coordination, database, or cloud sync.

## Future Ideas

- Import people and activities from an existing workbook.
- Optional holiday calendars.
- Optional per-person availability windows.
- Actual hours tracking.
- Simple charts in the dashboard tab.
- More Excel formatting for generated sheets.
