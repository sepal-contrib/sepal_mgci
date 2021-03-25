# It is strongly suggested to us a separate file to define the io of your tile and process. 
# it will help you to have control over it's fonctionality using object oriented programming

# in python variable are not mutable object (their value cannot be changed in a function)
# Thus use a class to define your input and output in order to have mutable variables
class DefaultProcessIo:
    def __init__(self):
        # set up your inputs
        self.slider_value = None
        self.text_value = None
    
        # set up your output
        self.link = None