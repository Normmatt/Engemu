import sys
from collections import deque

class Buffer(deque):
    def put(self, iterable):
        for i in iterable:
            self.append(i)
    def peek(self, how_many):
        return ''.join([self[i] for i in range(how_many)])
    def get(self, how_many):
        return ''.join([self.popleft() for _ in range(how_many)])

def get_num(buf):
	num = ""
	while len(buf) > 0 and buf.peek(1).isnumeric():
		num+= buf.get(1)
	return int(num)

def demangle_arg(buf):
	#print("debug", buf)
	isPointer = False
	isReference = False
	isUnsigned = False
	isConst = False
	isFunction = False
	hasTemplate = False
	hasNamespace = False
	arg = ""
	template = ""

	while arg == "":
		letter = buf.get(1)
		if letter == 'P':
			isPointer = True
		elif letter == 'R':
			isReference = True
		elif letter == 'U':
			isUnsigned = True
		elif letter == 'C':
			isConst = True
		elif letter == "F":
			isFunction = True
			arg = "(*)"
		elif letter == 't':
			hasTemplate = True
		elif letter == 'Q' and buf.peek(1) == '2':
			buf.get(1)
			hasNamespace = True
			arg = "::"
		elif letter == 'i':
			arg = "int"
		elif letter == 'd':
			arg = "double"
		elif letter == 'v':
			arg = "void"
		elif letter == 'c':
			arg = "char"
		elif letter == 's':
			arg = "short"	
		elif letter == 'l':
			arg = "long"			
		elif letter == 'f': #todo: check
			arg = "float" 
		elif letter == "G":
			#doesn't seems to do much
			letter = letter
		elif letter.isnumeric():
			buf.appendleft(letter)
			num = get_num(buf)
			arg = buf.get(num)
		else:
			print("unknow letter for demangling", letter)
			sys.exit(-1)

	if hasTemplate:
		#Todo: understand what they represent
		if buf.get(1) != "1":
			print("unknow template format for demangling")
			sys.exit(-1)
		temp_l = buf.get(1)
		if temp_l == 'Z':
			template = demangle_arg(buf)
		elif temp_l == 'i':
			template = str(get_num(buf))
		else:
			print("unknow template format for demangling")
			sys.exit(-1)

	if hasNamespace:
		arg = buf.get(get_num(buf)) + "::" + buf.get(get_num(buf))

	if isFunction and '_' in buf.peek(len(buf)):
		isPointer = False
		function_args = []
		m_function_args, rest = buf.peek(len(buf)).split('_')
		m_function_args = Buffer(m_function_args)
		buf.get(len(m_function_args) + 1)
		while len(m_function_args) > 0:
			function_args.append(demangle_arg(m_function_args))
		arg = demangle_arg(buf) + ' (*)(' + ', '.join(function_args) + ')'

	return ("unsigned " if isUnsigned else "") + arg + (("<" + template  + ">") if hasTemplate else "" ) + (" const" if isConst else "") + (" *" if isPointer else "") + (" &" if isReference else "") 

def demangle_args(mangled_args):
	buf = Buffer(mangled_args)
	args = []
	while len(buf) > 0:
		args.append(demangle_arg(buf))
		if len(buf) > 1 and buf.peek(1) == 'T':
			buf.get(1)
			repetition_num = get_num(buf)
			repetition_num -= 1
			while repetition_num > 0:
				args.append(args[-1])
				repetition_num -= 1

		elif len(buf) == 1 and buf.peek(1) == 'e':
			buf.get(1)
			args.append("...")

	return '(' + ', '.join(args) + ')'

def number_extract(txt):
	num = ""
	num_count = 0
	for i in range(0, len(txt)):
		if txt[i].isnumeric():
			num += txt[i]
			num_count+=1
		else:
			break
	return (txt[num_count:num_count+int(num)], txt[num_count+int(num):len(txt)])

def demangle_name(mangled):
	if len(mangled) == 0:
		return mangled
	elif mangled[0] == '.':
		#destructors
		if mangled[1] != '_':
			print("unknow desctructor format")
			sys.exit(-1)
		const = ""
		rest = mangled[2:len(mangled)]
		if rest[0] == "C":
			rest = rest[1:len(rest)]
			const = "const"
		
		if rest[0] == 't':
			#constructor
			rest = rest[1:len(rest)]
			namespace, args = number_extract(rest)
			args = args[2:len(args)]
			return namespace + "::" +  namespace + demangle_args(args) + const
		else:
			#destructor
			namespace, args = number_extract(rest)
			return namespace + "::~" +  namespace + "()" + const
	elif mangled[0] == '_' and mangled[1].isnumeric():
		#constructors
		const = ""
		rest = mangled[1:len(mangled)]
		if(rest[0] == "C"):
			rest = rest[1:len(rest)]
			const = "const"
		namespace, args = number_extract(rest)
		return namespace + "::" +  namespace + demangle_args(args) + const
	else:
		if "__" not in mangled:
			return mangled
		else:
			const = ""
			fname, rest = mangled.split("__")
			if rest[0] == "C":
				rest = rest[1:len(rest)]
				const = "const"
			if rest[0].isnumeric():
				#has a namespace
				namespace, args = number_extract(rest)
				return namespace + "::" +  fname + demangle_args(args) + const
			else:
				return fname + demangle_args(rest) + const

#key : ordinal
#value : address
exports = dict()

#key : ordinal
#value : name
idt = dict()

#Load exports
with open("Euser.exports") as f:
	for line in f:
		line = line.rstrip()
		ordinal, address = line.split(": ")
		if ordinal in exports:
			print("an ordinal can not appears 2 time in the export list:", ordinal)
			sys.exit(-1)
		exports[ordinal] = address


#Load idt
with open("euser.idt") as f:
	for line in f:
		line = line.rstrip()
		if line != "" and line != " ":
			ordinal, name = line.split(" Name=")
			if ordinal in idt:
				print("an ordinal can not appears 2 time in the id list:", ordinal)
				sys.exit(-1)
			idt[ordinal] = name


#produce address: name
for ordinal in exports:
	if ordinal not in idt:
		print(ordinal, "is not in both table")
		sys.exit(-1)
	address = exports[ordinal]
	name = idt[ordinal]
	print(name)
	print(address + ": " + demangle_name(name))


#tests
# print(demangle_name("PageSizeInBytes__7UserHalRi"))
# print(demangle_name("newL__5CBaseUi"))
# print(demangle_name("BinarySearchUnsigned__C17RPointerArrayBasePUiRi"))
# print(demangle_name("CalibrationPoints__7UserHalR21TDigitizerCalibration"))
# print(demangle_name("BuildVarArrayL__13CArrayPakBaseRPt13CArrayVarFlat1Zv"))
# print(demangle_name("Print__6RDebugGt11TRefByValue1ZC7TDesC16e"))
# print(demangle_name("AppendFormat__6TDes16Gt11TRefByValue1ZC7TDesC16P14TDes16Overflowe"))
# print(demangle_name("Pow10__4MathRdi"))
# print(demangle_name("Pow__4MathRdRCdT2"))
# print(demangle_name("_5RHeapRC6RChunkiiii"))
# print(demangle_name("_5RHeapi"))
# print(demangle_name("._5RHeap"))
# print(demangle_name("._10CCirBuffer"))
# print(demangle_name("_DbgMarkEnd__4UserQ25RHeap12TDbgHeapTypei"))
# print(demangle_name("PanicTFixedArray__Fv"))
# print(demangle_name("DummyEuser_1659__Fv"))
# print(demangle_name("Next__10TFindMutexRt4TBuf1i256"))
# print(demangle_name("StringLength__4UserPCUs"))
# print(demangle_name("SetExceptionHandler__7RThreadPF8TExcType_vUl"))
# print(demangle_name("Find__C10RArrayBasePCvPFPCvPCv_i"))
# print(demangle_name("IsPresent__C8TUidTypeG4TUid"))
# print(demangle_name("._t13CArrayFixFlat1Zi"))
# print(demangle_name("._t13CArrayFixFlat1Z4TUidi"))