class X_Value:

    def __init__(self, index = 0):

        self.name = ''
        self.begin = None
        self.end = None
        self.value = None
        self.index = index
		
    def init(self, x_ranges):

        self.name = x_ranges['name']
        self.begin = x_ranges['begin']
        self.end = x_ranges['end']
        self.value = self.begin
		
class Y_Value:

    def __init__(self, index = 0, name = ''):
	
        self.name = name
        self.type = None
        self.lowerbound = None
        self.importance = 1
        self.value = None
        self.index = index

    def init(self, y_type):

        self.type = y_type
        if y_type == 1:
            self.lowerbound = 0
            
def indent(elem, level = 0):

    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            indent(elem, level+1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i