import functools

# Definition of decorator that is receiving two arguments
def loading(btn, alert):
    def decorator_loading(func):
        @functools.wraps(func)
        def wrapper_loading(*args, **kwargs):
            btn.loading=True
            try:
                value = func(*args, **kwargs)
            except Exception as e:
                btn.loading=False
                alert.add_msg(f'{e}', type_='error')
                raise e
            btn.loading=False
            return value
        return wrapper_loading
    return decorator_loading