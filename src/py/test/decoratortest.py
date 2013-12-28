
def deco(fn):
    xval = 4 
    def wrapped(args):
        xval = 3
        print "xval", xval
        fn(args)
    return wrapped


@deco
def myfun(yval):
    print "yval=", yval
    print "xval=", xval
    return

def bold(fn):
    def wrapped():
        return '<b>' + fn() + '</b>'
    return wrapped

@bold
def printhello():
    return "hello"


printhello()

