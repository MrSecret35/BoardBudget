# BoardBudget

BoardBudget is a small local planning tool for allocating people to project activities based on estimated hours.

One board is one `.xlsx` file. The Excel file is both the app storage format and the export format, so boards stay easy to inspect, copy, send, archive, and edit outside the app when needed.

BoardBudget is intentionally simple:

- no database
- no login
- no cloud sync
- no API layer
- Python performs the planning calculations
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

The app stores boards in the local `boards/` folder. Generated exports can be saved or downloaded as normal Excel files.

## Create A Board

From the sidebar you can:

- create a new empty board
- create the Pitagora sample board
- open an existing `.xlsx` board
- duplicate the selected board
- recalculate generated sheets
- download the current board file

## Edit Data

BoardBudget uses editable tables with explicit save buttons. It does not autosave on every cell edit.

Use the tabs to edit:

- `People`: `person_id`, `name`, `hours_per_day`, `active`
- `Activities`: `activity_id`, `order`, `name`, `estimated_hours`, `max_hours_per_day`, `status`, `notes`
- `Assignments`: `activity_id`, `person_id`

After changing inputs, click the relevant save button. Then use **Recalculate current board** in the sidebar to regenerate calendar, dashboard, and warnings sheets.

## Excel Sheet Format

Every board workbook contains these sheets:

### 01_Board

| key | value |
| --- | --- |
| board_name | Pitagora May 2026 |
| start_date | 2026-05-13 |
| hours_per_day | 8 |
| working_days | MON,TUE,WED,THU,FRI |

### 02_People

| person_id | name | hours_per_day | active |
| --- | --- | --- | --- |
| P1 | Person 1 | 8 | TRUE |
| P2 | Person 2 | 8 | TRUE |

### 03_Activities

| activity_id | order | name | estimated_hours | max_hours_per_day | status | notes |
| --- | --- | --- | --- | --- | --- | --- |
| A1 | 1 | Analysis | 16 | 8 | PLANNED | |

Allowed statuses are `PLANNED`, `DONE`, and `CANCELLED`.

### 04_Assignments

| activity_id | person_id |
| --- | --- |
| A1 | P1 |

### Generated Sheets

The app replaces these sheets when recalculating:

- `05_Calendar`
- `06_Dashboard`
- `07_Warnings`

Do not manually edit generated sheets unless you are intentionally making an external copy.

## Planning Rules

- Planning is in hours.
- Default capacity is 8 hours per person per day.
- Working days are Monday to Friday.
- Holidays, vacations, sick leave, and part-time exceptions are ignored in v1.
- Activity `order` is a priority, not a global dependency.
- Shared activities are independent per person.
- If an activity is assigned to multiple people, estimated hours are split equally.
- Each person is filled up to daily capacity when possible.
- `max_hours_per_day` limits each assigned person on that activity for that date.
- A person can work on multiple activities in the same day.
- `DONE` and `CANCELLED` activities are skipped.
- Activities without assignments or with invalid estimated hours produce warnings.
- Planning is deterministic: activities sort by `order`, then `activity_id`.
- Planning stops after a safe maximum of 730 calendar days and reports an error if work remains.

## Known v1 Limitations

- No holiday calendar.
- No vacations or individual availability exceptions.
- No dependencies beyond simple priority ordering.
- No resource skills or roles.
- No authentication or multi-user coordination.
- No database.

## Future Ideas

- Import people and activities from an existing workbook.
- Optional holiday calendars.
- Optional per-person availability windows.
- Simple charts in the dashboard tab.
- More Excel formatting for generated sheets.

