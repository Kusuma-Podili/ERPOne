"""Registry for approved report data fields. Keeps report configuration explicit."""
FIELDS={
 'organizations':['id','name','code','created_at'],
 'crm':['id','name','account_type','created_at'],
 'sales':['id','status','total_amount','created_at'],
 'inventory':['id','sku','name','quantity'],
 'procurement':['id','status','created_at'],
 'finance':['id','status','created_at'],
 'hr':['id','employee_number','status','created_at'],
 'payroll':['id','status','created_at'],
 'projects':['id','code','name','status','budget','progress_percent'],
 'support':['id','number','status','priority','created_at'],
}
def allowed_fields(source): return tuple(FIELDS.get(source,()))
def validate_columns(source, columns):
    allowed=set(allowed_fields(source)); requested=[str(c) for c in columns]
    invalid=[c for c in requested if c not in allowed]
    if invalid: raise ValueError(f'Unsupported fields for {source}: {", ".join(invalid)}')
    return requested
