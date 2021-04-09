import functools

# Definition of decorator that is receiving two arguments
def loading(alert, dialog, btn=None):
    def decorator_loading(func):
        @functools.wraps(func)
        def wrapper_loading(*args, **kwargs):
            if btn : btn.loading=True
            try:
                value = func(*args, **kwargs)
            except Exception as e:
                if btn : btn.loading=False
                alert.add_msg(f'{e}', type_='error')
                dialog.alert(alert)
                raise e
            if btn : btn.loading=False
            return value
        return wrapper_loading
    return decorator_loading