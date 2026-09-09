"""Small serialization helpers used by analytics views and exports."""
from decimal import Decimal
from datetime import date, datetime

def json_value(value):
    if isinstance(value,Decimal): return float(value)
    if isinstance(value,(datetime,date)): return value.isoformat()
    return value

def serialize_row(row): return {key:json_value(value) for key,value in row.items()}
def serialize_rows(rows): return [serialize_row(row) for row in rows]

def csv_rows(columns, rows):
    output=[','.join(columns)]
    for row in rows:
        output.append(','.join('' if row.get(c) is None else str(json_value(row.get(c))).replace(',',' ') for c in columns))
    return '\n'.join(output)+'\n'
