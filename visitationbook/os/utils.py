def strtodate(datestr="", format="%Y-%m-%d"):
    from datetime import datetime
    if not datestr:
        return datetime.today().date()
    return datetime.strptime(datestr, format).date()