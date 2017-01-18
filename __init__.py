pint_ureg = None
try:
    import pint
    # this is just to make sure everybody uses the same ureg
    pint_ureg = pint.UnitRegistry()
except ImportError:
    pass
