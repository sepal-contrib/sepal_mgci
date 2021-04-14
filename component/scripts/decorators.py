import functools
import sepal_ui.sepalwidgets as sw


# Definition of decorator that is receiving two arguments
def loading(dialog, btn=None):
    """Decorator to toggle loading a button and display errors on a dialog
    
    Args:
        dialog (Dialog) : Custom dialog with Output children
        btn (sw.Btn, v.Btn) : Event button 
    """
    
    def decorator_loading(func):
        @functools.wraps(func)
        def wrapper_loading(*args, **kwargs):
            if btn : btn.loading=True
            try:
                value = func(*args, **kwargs)
            except Exception as e:
                
                if btn : btn.loading=False
                dialog.v_model = True
                
                with dialog.output:
                    display(sw.Alert().add_msg(f'{e}', type_='error').show())
                    
            if btn : btn.loading=False

        return wrapper_loading
    return decorator_loading

# Necesito el output como children del dialog
# Luego dentro del decorador puedo limpiar el dialog y mostrar el aviso