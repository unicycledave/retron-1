#!/usr/bin/python
#
# Microcode ROM builder for Retron-1 TTL CPU. 
#
# This script will output three images in either logisim format or as a raw binary dump for writing to EEPROMs for each instruction in the set. 
#
# Completed CPU steps - need temporary memory peek mechanism for absolute addresses
#					> store two mem cycles in PC_U and PC_L, temporarily override PC with their values
#					> triggers on a MEM_BUS command since the o/p goes to mem bus anyhow
#					> thus, a MUX / control is needed?
#
# Musings on stuff remaining to complete:
#	> ensure that flags registers are set correctly where required
#	>+ figure out interrupt checking and handling
#		> interrupt flag can be set in software or triggered via hw
#		> how many hw interrupts? 
#	>+ implement rol
#	> implement ror (harder)
#	>+ ensure carry flag is used correctly for add
#	>+ ensure OF flag is used correctly for sub
#	>+ ensure stack pointer stuff works right
#	> implement CMP and ensure flags checking is done correctly
# FLAGS: INT / Z / C
# 
# Flags musings: flags check flag (FLAGS_EVAL) must be set in addition to D_FL_EC or D_FL_ZC instead of an iteration after.


# required junk:
instr = []

# ROM0 mapping:
INV_FLAG= [[0x80],[0x00],[0x00]]	# Enables FLAGS checking, as well as a synonym for ALT_MEM
X		= [[0x40],[0x00],[0x00]]
SIC_RST = [[0x20],[0x00],[0x00]]
PC_CLK	= [[0x10],[0x00],[0x00]]
REG_SET = [[0x0F],[0x00],[0x00]]

# ROM1 mapping:
ALU_INB	= [[0x00],[0x0F],[0x00]]
MEM_BUS = [[0x00],[0xF0],[0x00]] 

# ROM2 mapping:
PC_GLOB = [[0x00],[0x00],[0x01]]
PC_LOAD = [[0x00],[0x00],[0x02]]
ALU_M	= [[0x00],[0x00],[0x04]]
SET_FLAG= [[0x00],[0x00],[0x08]]
ALU_SEL	= [[0x00],[0x00],[0xF0]]

# REG_SET mapping:
S_NULL	= [[0x00],[0x00],[0x00]] 
S_ACC	= [[0x01],[0x00],[0x00]]
S_X		= [[0x02],[0x00],[0x00]]
S_Y		= [[0x03],[0x00],[0x00]]
S_MEM_U	= [[0x04],[0x00],[0x00]] 
S_MEM_L	= [[0x05],[0x00],[0x00]] 
S_PC_U	= [[0x06],[0x00],[0x00]]
S_PC_L	= [[0x07],[0x00],[0x00]]
S_ALU	= [[0x08],[0x00],[0x00]]
MEM_WR	= [[0x09],[0x00],[0x00]]
S_MEZZ  = [[0x0A],[0x00],[0x00]]
WR_STACK= [[0x0B],[0x00],[0x00]]
S_SP_H	= [[0x0C],[0x00],[0x00]]
ALL_FLAGS=[[0x0D],[0x00],[0x00]]	# for setting all flags
# available
# available

# MEM_BUS mapping:
D_MEM	= [[0x00],[0x00],[0x00]]
ALT_MEM	= [[0x00],[0x10],[0x00]]
D_X		= [[0x00],[0x20],[0x00]]
D_Y		= [[0x00],[0x30],[0x00]]
D_MEM_U	= [[0x00],[0x40],[0x00]]
D_MEM_L	= [[0x00],[0x50],[0x00]]
D_FL_OF	= [[0x00],[0x60],[0x00]]
D_FL_CARRY= [[0x00],[0x70],[0x00]]
D_ALU	= [[0x00],[0x80],[0x00]]
D_ACC	= [[0x00],[0x90],[0x00]] 
D_U_PCO	= [[0x00],[0xA0],[0x00]]
D_L_PCO	= [[0x00],[0xB0],[0x00]] 
D_FL_I	= [[0x00],[0xC0],[0x00]]
D_FL_SIGN= [[0x00],[0xD0],[0x00]]
D_FL_EC = [[0x00],[0xE0],[0x00]] # Equals-compare flag for JE/JNE
D_FL_ZC = [[0x00],[0xF0],[0x00]] # Zero-compare flag for JZ/JNZ

# ALU_B mapping
A_NULL	= [[0x00],[0x00],[0x00]]
A_ACC	= [[0x00],[0x01],[0x00]]
A_X		= [[0x00],[0x02],[0x00]]
A_Y		= [[0x00],[0x03],[0x00]]
A_MEM_U	= [[0x00],[0x04],[0x00]]
A_MEM_L	= [[0x00],[0x05],[0x00]]
A_ALU	= [[0x00],[0x06],[0x00]]	
A_MEM	= [[0x00],[0x07],[0x00]]
ROM_DISABLE= [[0x00],[0x08],[0x00]]
X		= [[0x00],[0x09],[0x00]]
D_FLAGS	= [[0x00],[0x0A],[0x00]]
DEC_STACK= [[0x00],[0x0B],[0x00]]
INC_STACK= [[0x00],[0x0C],[0x00]]
X		= [[0x00],[0x0D],[0x00]]
X		= [[0x00],[0x0E],[0x00]]
X		= [[0x00],[0x0F],[0x00]]

# ALU select mapping - 
ALU_NOTA		= [[0x00],[0x00],[0x00]]
ALU_NOT_AORB	= [[0x00],[0x00],[0x10]]
ALU_NOTA_ANDB	= [[0x00],[0x00],[0x20]]
ALU_ZERO		= [[0x00],[0x00],[0x30]]
ALU_AANDBNOT	= [[0x00],[0x00],[0x40]]
ALU_NOTB		= [[0x00],[0x00],[0x50]]
ALU_AXORB		= [[0x00],[0x00],[0x60]]
ALU_AAND_NOTB	= [[0x00],[0x00],[0x70]]
ALU_NOTA_ORB	= [[0x00],[0x00],[0x80]]
ALU_NOT_AXORB	= [[0x00],[0x00],[0x90]]
ALU_DISPB		= [[0x00],[0x00],[0xA0]]
ALU_AANDB		= [[0x00],[0x00],[0xB0]]
ALU_ONE			= [[0x00],[0x00],[0xC0]]
ALU_AOR_NOTB	= [[0x00],[0x00],[0xD0]]
ALU_AORB		= [[0x00],[0x00],[0xE0]]
ALU_DISPA		= [[0x00],[0x00],[0xF0]]


# the format of each instruction is a list of lists, each sub-list containing the action to be taken during that sub-instruction.

# 0x00 NOP 
instr.append([[0x00],
[0x000,S_MEZZ,PC_CLK],				# Load opcode register
[0x100,SIC_RST]])					# Increment PC, SIC reset

# 0x01 JMP abs
instr.append([[0x01],
[0x000,S_MEZZ,PC_CLK],					# Load opcode register	
[0x100,PC_CLK,S_PC_U],					# Increment PC, save value to PC_U
[0x200,S_PC_L],							# Increment PC, save value to PC_L
[0x300,PC_LOAD,PC_GLOB,SIC_RST]])		# Enable PC_LOAD, Toggle PC_GLOB, reset SIC

# 0x02 JMP - jump to address in MEM reg
instr.append([[0x02],
[0x000,S_MEZZ,PC_CLK],						# Load opcode register
[0x100,D_MEM_U,S_PC_U],				# Disable MEM, save MEM_U to PC_U
[0x200,D_MEM_L,S_PC_L],				# Disable MEM, save MEM_L to PC_L
[0x300,PC_LOAD,PC_GLOB,SIC_RST]])			# Enable PC_LOAD, Toggle PC_GLOB, reset SIC

# 0x03 JZ abs - jump to absolute value if zero flag set
instr.append([[0x03],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],		
[0x200,PC_CLK,S_PC_L],	
[0x300,D_FL_ZC,SIC_RST],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x04 JZ - jump to value in MEM register if zero flag set
instr.append([[0x04],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],	
[0x200,D_MEM_L,S_PC_L],
[0x300,SIC_RST,D_FL_ZC],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x05 JNZ abs - jump to absolute address stored in operand if zero flag not set
instr.append([[0x05],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],		
[0x200,PC_CLK,S_PC_L],	
[0x300,D_FL_ZC,INV_FLAG,SIC_RST],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x06 JNZ - jump to value in MEM register if zero flag not set
instr.append([[0x06],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],	
[0x200,D_MEM_L,S_PC_L],
[0x300,SIC_RST,D_FL_ZC,INV_FLAG],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x07 JE abs - jump to absolute address if equal flag is set
instr.append([[0x07],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],					# set pc_u, increment clock
[0x200,PC_CLK,S_PC_L],					# set pc_l, increment clock
[0x300,D_FL_EC,SIC_RST],		# FLAGS_EVAL impedes SIC_RST if FLAG=1
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x08 JE - jump to MEM register value if equal flag is set
instr.append([[0x08],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],			
[0x200,D_MEM_L,S_PC_L],		
[0x300,D_FL_EC,SIC_RST],	
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])	

# 0x09 JNE abs - jump to absolute address if equal flag is not set
instr.append([[0x09],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],			
[0x200,PC_CLK,S_PC_L],		
[0x300,D_FL_EC,INV_FLAG,SIC_RST],	
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])	
	
# 0x0A JNE - jump to MEM register value if equal flag is set
instr.append([[0x0A],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],			
[0x200,D_MEM_L,S_PC_L],		
[0x300,D_FL_EC,INV_FLAG,SIC_RST],	
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])	

# 0x10 INC ACC
instr.append([[0x10],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],		# this sets ALU_Cn to on
[0x200,D_ACC,ALU_NOTA,S_ALU],		# Disable MEM, save ACC to ALU and set ALU to add 1
[0x300,D_ALU,S_ACC],					# Disable MEM, save ALU to ACC
[0x400,SIC_RST]])

# 0x11 DEC ACC
instr.append([[0x11],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_ACC,ALU_DISPA,S_ALU],
[0x300,D_ALU,S_ACC],						# Disable MEM, save ALU to ACC
[0x400,SIC_RST]])

# 0x12 INC X
instr.append([[0x12],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],
[0x200,D_X,ALU_NOTA,S_ALU],				# Disable MEM, save X to ALU and set ALU to add 1
[0x300,D_ALU,S_X],						# Disable MEM, save ALU to X
[0x400,SIC_RST]])

# 0x13 DEC X
instr.append([[0x13],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_X,ALU_DISPA,S_ALU],		# Disable MEM, save X to ALU and set ALU to subtract 1
[0x300,D_ALU,S_X],						# Disable MEM, save ALU to X 
[0x400,SIC_RST]])

# 0x14 INC Y
instr.append([[0x14],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],
[0x200,D_Y,ALU_NOTA,S_ALU],			# Disable MEM, save Y to ALU and set ALU to add 1
[0x300,D_ALU,S_Y],					# Disable MEM, save ALU to Y	
[0x400,SIC_RST]])

# 0x15 DEC Y
instr.append([[0x15],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_Y,ALU_DISPA,S_ALU],		# Disable MEM, Save Y to ALU and set ALU to subtract 1
[0x300,D_ALU,S_Y],						# Disable MEM, save ALU to Y
[0x400,SIC_RST]])

# 0x16 INC MEM_L
instr.append([[0x16],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],
[0x200,D_MEM_L,ALU_NOTA,S_ALU],			# Disable MEM, Save MEM_U to ALU and set ALU to add 1
[0x300,D_ALU,S_MEM_L],					# Disable MEM, save ALU to MEM_U
[0x400,SIC_RST]])

# 0x17 DEC MEM_L
instr.append([[0x17],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_MEM_L,ALU_DISPA,S_ALU],
[0x300,D_ALU,S_MEM_L],
[0x400,SIC_RST]])

# 0x18 INC MEM_U
instr.append([[0x18],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],
[0x200,D_MEM_U,ALU_NOTA,S_ALU],			# Disable MEM, Save MEM_U to ALU and set ALU to add 1
[0x300,D_ALU,S_MEM_U],					# Disable MEM, save ALU to MEM_U
[0x400,SIC_RST]])

# 0x19 DEC MEM_U
instr.append([[0x19],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_MEM_U,ALU_DISPA,S_ALU],
[0x300,D_ALU,S_MEM_U],
[0x400,SIC_RST]])

# 0x1A ADD ACC imm - add immediate to accumulator
instr.append([[0x1A],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,ALU_NOT_AXORB,S_ALU],		# Set ALU to add mode, ALU_INB + MEM. Save to ALU register.
[0x200,D_ALU,S_ACC],						# Disable MEM, save ALU to ACC
[0x300,PC_CLK,SIC_RST]])

# 0x1B ADD ACC abs - add value from abs to accumulator
instr.append([[0x1B],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_ACC,ALU_NOT_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x1C ADD ACC X - add X to accumulator
instr.append([[0x1C],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_X,ALU_NOT_AXORB,S_ALU],	# Set ALU to add mode, X + ACC. Save to ALU register.
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x1D ADD ACC Y - add Y to accumulator
instr.append([[0x1D],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_Y,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x1E ADD ACC MEM_U - add MEM_U to accumulator
instr.append([[0x1E],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_MEM_U,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x1F ADD ACC MEM_L - add MEM_L to accumulator
instr.append([[0x1F],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x20 ADD X imm - add imm to X
instr.append([[0x20],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_X,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],					
[0x300,SIC_RST]])

# 0x21 ADD X abs - add the value from abs to X
instr.append([[0x21],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_X,ALU_NOT_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x22 ADD X Y - add X to Y
instr.append([[0x22],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_Y,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x23 ADD X MEM_U - add X to MEM_U
instr.append([[0x23],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_MEM_U,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x24 ADD X MEM_L - add X to MEM_L
instr.append([[0x24],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x25 ADD Y imm - Add immediate to Y
instr.append([[0x25],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_Y,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x26 ADD Y abs - Add value from abs to Y
instr.append([[0x26],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_Y,ALU_NOT_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x27 ADD Y MEM_U - Add MEM_U to Y
instr.append([[0x27],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_Y,D_MEM_U,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x28 ADD Y MEM_L - Add MEM_L to Y
instr.append([[0x28],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_Y,D_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x29 ADD MEM_U imm
instr.append([[0x29],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM_U,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x2A ADD MEM_U abs
instr.append([[0x2A],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_MEM_U,ALU_NOT_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x2B ADD MEM_U MEM_L
instr.append([[0x2B],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_MEM_U,D_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x2C ADD MEM_L imm
instr.append([[0x2C],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x2D ADD MEM_L abs
instr.append([[0x2D],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_MEM_L,ALU_NOT_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x2E SUB ACC imm
instr.append([[0x2E],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM,D_ACC,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x2F SUB ACC abs
instr.append([[0x2F],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,A_MEM,D_ACC,ALU_AXORB,S_ALU],	# SET_FLAG is ALT_MEM for ALU Bus
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x30 SUB ACC X
instr.append([[0x30],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,A_X,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x31 SUB ACC Y
instr.append([[0x31],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,A_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x32 SUB ACC MEM_U
instr.append([[0x32],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,A_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x33 SUB ACC MEM_L
instr.append([[0x33],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,A_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x34 SUB X imm
instr.append([[0x34],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM,D_X,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x35 SUB X abs
instr.append([[0x35],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,A_MEM,D_X,ALU_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x36 SUB X ACC
instr.append([[0x36],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_X,A_ACC,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x37 SUB X Y
instr.append([[0x37],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_X,A_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x38 SUB X MEM_U
instr.append([[0x38],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_X,A_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x39 SUB X MEM_L
instr.append([[0x39],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_X,A_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x3A SUB Y imm
instr.append([[0x3A],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM,D_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x3B SUB Y abs
instr.append([[0x3B],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,A_MEM,D_Y,ALU_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x3C SUB Y ACC
instr.append([[0x3C],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x3D SUB Y X
instr.append([[0x3D],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x3E SUB Y MEM_U
instr.append([[0x3E],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_MEM_U,D_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x3F SUB Y MEM_L
instr.append([[0x3F],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_MEM_L,D_Y,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x40 SUB MEM_U imm
instr.append([[0x40],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM,D_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x41 SUB MEM_U abs
instr.append([[0x41],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,A_MEM,D_MEM_U,ALU_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x42 SUB MEM_U ACC
instr.append([[0x42],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x43 SUB MEM_U X
instr.append([[0x43],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x44 SUB MEM_U Y
instr.append([[0x44],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_Y,D_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x45 SUB MEM_U MEM_L
instr.append([[0x45],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_MEM_L,D_MEM_U,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x46 SUB MEM_L imm
instr.append([[0x46],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_MEM,D_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x47 SUB MEM_L abs
instr.append([[0x47],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,A_MEM,D_MEM_L,ALU_AXORB,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x48 SUB MEM_L ACC
instr.append([[0x48],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x49 SUB MEM_L X
instr.append([[0x49],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_X,D_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x4A SUB MEM_L Y
instr.append([[0x4A],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_Y,D_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x4B SUB MEM_L MEM_U
instr.append([[0x4B],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_MEM_U,D_MEM_L,ALU_AXORB,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x4C HLT
instr.append([[0x4C],
[0x000,S_MEZZ],
[0x100,SIC_RST]])

# 0x4D JC - Jump on carry flag set
instr.append([[0x4D],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],	
[0x200,D_MEM_L,S_PC_L],
[0x300,SIC_RST,D_FL_CARRY],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x4E JNC - Jump on carry flag not set
instr.append([[0x4E],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],	
[0x200,D_MEM_L,S_PC_L],
[0x300,SIC_RST,INV_FLAG,D_FL_CARRY],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x4F JC abs 
instr.append([[0x4F],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],		
[0x200,PC_CLK,S_PC_L],	
[0x300,D_FL_CARRY,SIC_RST],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x50 JNC abs 
instr.append([[0x50],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],		
[0x200,PC_CLK,S_PC_L],	
[0x300,D_FL_CARRY,INV_FLAG,SIC_RST],
[0x400,SIC_RST,PC_LOAD,PC_GLOB]])

# 0x51 STO - store ACC to value saved in MEM registers
instr.append([[0x51],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],
[0x200,D_MEM_L,S_PC_L],
[0x300,D_ACC,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x52 STO X
instr.append([[0x52],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],
[0x200,D_MEM_L,S_PC_L],
[0x300,D_X,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x53 STO Y
instr.append([[0x53],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,S_PC_U],
[0x200,D_MEM_L,S_PC_L],
[0x300,D_Y,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x54 NOP (reserved)
# 0x55 NOP (reserved)

# 0x56 NOT imm - store inverse of imm into acumulator
instr.append([[0x56],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x57 NOT abs - store inverse of abs into accumulator
instr.append([[0x57],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,ALU_M,ALU_NOTA,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0x58 NOT ACC
instr.append([[0x58],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x59 NOT X
instr.append([[0x59],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_X,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x5A NOT Y
instr.append([[0x5A],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_Y,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x5B NOT MEM_U
instr.append([[0x5B],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_U,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0x5C NOT MEM_L
instr.append([[0x5C],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_MEM_L,ALU_M,ALU_NOTA,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# -- debugged to here --

# 0x5D SHL imm
instr.append([[0x5D],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,PC_CLK,ALU_ONE,S_ALU],					# A * 2 = SHL 1, then save to ALU
[0x300,D_ALU,S_ACC],
[0x400,SIC_RST]])

# 0x5E SHL abs
instr.append([[0x5E],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x400,ALT_MEM,ALU_ONE,S_ALU],
[0x500,D_ALU,S_ACC],
[0x600,SIC_RST]])

# 0x5F SHL ACC
instr.append([[0x5F],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_ACC,ALU_ONE,S_ALU],
[0x300,D_ALU,S_ACC],
[0x400,SIC_RST]])

# 0x60 SHL X
instr.append([[0x60],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_X,ALU_ONE,S_ALU],
[0x300,D_ALU,S_X],
[0x400,SIC_RST]])

# 0x61 SHL Y
instr.append([[0x61],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_Y,ALU_ONE,S_ALU],
[0x300,D_ALU,S_Y],
[0x400,SIC_RST]])

# 0x62 SHL MEM_U
instr.append([[0x62],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_MEM_U,ALU_ONE,S_ALU],
[0x300,D_ALU,S_MEM_U],
[0x400,SIC_RST]])

# 0x63 SHL MEM_L
instr.append([[0x63],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],
[0x200,D_MEM_L,ALU_ONE,S_ALU],
[0x300,D_ALU,S_MEM_L],
[0x400,SIC_RST]])

# --- snip ---

# 0x79 CMP imm
instr.append([[0x79],
[0x000,S_MEZZ,PC_CLK],						# Compare ACC and current mem:
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x200,A_ACC,ALU_AXORB,S_ALU],		# AXORB is the subtract mode, which is also the compare mode.
[0x300,PC_CLK,SIC_RST]])		

# 0x7A CMP abs
instr.append([[0x7A],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x400,A_ACC,ALU_AXORB,ALT_MEM,S_ALU],
[0x500,SIC_RST]])

# 0x7B CMP X
instr.append([[0x7B],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x200,D_X,A_ACC,ALU_AXORB,S_ALU],
[0x300,SIC_RST]])

# 0x7C CMP Y
instr.append([[0x7C],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x200,D_Y,A_ACC,ALU_AXORB,S_ALU],
[0x300,SIC_RST]])

# 0x7D CMP MEM_U
instr.append([[0x7D],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x200,D_MEM_U,A_ACC,ALU_AXORB,S_ALU],
[0x300,SIC_RST]])

# 0x7E CMP MEM_L
instr.append([[0x7E],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG],		# this sets ALU_Cn to on
[0x200,D_MEM_L,A_ACC,ALU_AXORB,S_ALU],
[0x300,SIC_RST]])

# 0x7F NOP (reserved)

# 0x80 STO imm abs
instr.append([[0x80],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,ALU_M,ALU_DISPA,S_ALU],		# set ALU reg to imm value
[0x200,PC_CLK,S_PC_U],
[0x300,PC_CLK,S_PC_L],	
[0x400,D_ALU,MEM_WR,SET_FLAG,ALU_AXORB],	# set mem addr to value of alu
[0x500,SIC_RST]])

# 0x81 STO ACC abs
instr.append([[0x81],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,D_ACC,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x82 STO X abs
instr.append([[0x82],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,D_X,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x83 STO Y abs
instr.append([[0x83],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,D_Y,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x84 NOP (reserved)

# 0x85 STO MEM_U abs
instr.append([[0x85],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,D_MEM_U,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x86 STO MEM_L abs
instr.append([[0x86],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,D_MEM_L,MEM_WR,SET_FLAG,ALU_AXORB],
[0x400,SIC_RST]])

# 0x87 LOA ACC abs - load the value from abs into the accumulator
instr.append([[0x87],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,S_ACC],
[0x400,SIC_RST]])

# 0x88 LOA X abs
instr.append([[0x88],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,S_X],
[0x400,SIC_RST]])

# 0x89 LOA Y abs
instr.append([[0x89],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,S_Y],
[0x400,SIC_RST]])

# 0x8A LOA ACC imm
instr.append([[0x8A],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_ACC],
[0x200,PC_CLK,SIC_RST]])
	
# 0x8B LOA X imm
instr.append([[0x8B],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_X],
[0x200,PC_CLK,SIC_RST]])

# 0x8C LOA Y imm
instr.append([[0x8C],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_Y],
[0x200,PC_CLK,SIC_RST]])

# 0x8D LOA MEM_U imm
instr.append([[0x8D],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_U],
[0x200,PC_CLK,SIC_RST]])

# 0x8E LOA MEM_L imm
instr.append([[0x8E],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_L],
[0x200,PC_CLK,SIC_RST]])

# 0x8F NOP (reserved)
# 0x90 NOP (reserved)
instr.append([[0x90],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,ROM_DISABLE], 
[0x200,SIC_RST]])

# 0x91 LOA MEM_U abs
instr.append([[0x91],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,S_MEM_U],
[0x400,SIC_RST]])

# 0x92 LOA MEM_L abs
instr.append([[0x92],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,S_MEM_L],
[0x400,SIC_RST]])


# 0x93 CLC - clear carry
instr.append([[0x93],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY,INV_FLAG], 
[0x200,SIC_RST]])

# 0x94 CLI - clear interrupt
instr.append([[0x94],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_I,INV_FLAG],
[0x200,SIC_RST]])

# 0x95 CLO - clear overflow
instr.append([[0x95],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_OF,INV_FLAG],
[0x200,SIC_RST]])

# 0x96 SFC
instr.append([[0x96],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_CARRY],
[0x200,SIC_RST]])

# 0x97 SFI 
instr.append([[0x97],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_I],
[0x200,PC_CLK,SIC_RST]])

# 0x98 SFO
instr.append([[0x98],
[0x000,S_MEZZ,PC_CLK],
[0x100,SET_FLAG,D_FL_OF],
[0x200,PC_CLK,SIC_RST]])

# 0x99 JSR abs 
instr.append([[0x99],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L,INC_STACK],					# 3*pc_clk before saving ensures return to correct mem.
[0x300,WR_STACK,INC_STACK,D_U_PCO],
[0x400,WR_STACK,INC_STACK,D_L_PCO],
[0x500,WR_STACK,D_FLAGS,D_FL_CARRY],
[0x600,PC_LOAD,PC_GLOB,SIC_RST]])		# Enable PC_LOAD, Toggle PC_GLOB, reset SIC

# 0x9A RETS
instr.append([[0x9A],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,ALL_FLAGS],
[0x200,DEC_STACK,S_PC_L],
[0x300,DEC_STACK,S_PC_U],
[0x400,PC_LOAD,PC_GLOB,SIC_RST]])

# 0x9B RETI

# -- snip --

# 0xA0 NOP (reserved)

# 0xA1 SSP
instr.append([[0xA1],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_SP_H],
[0x200,PC_CLK,SIC_RST]])

# 0xA2 PUSH ACC
instr.append([[0xA2],
[0x000,S_MEZZ,PC_CLK],
[0x100,INC_STACK],
[0x200,WR_STACK,D_ACC],
[0x300,SIC_RST]])

# 0xA3 PUSH X
instr.append([[0xA3],
[0x000,S_MEZZ,PC_CLK],
[0x100,INC_STACK],
[0x200,WR_STACK,D_X],
[0x300,SIC_RST]])

# 0xA4 PUSH Y
instr.append([[0xA4],
[0x000,S_MEZZ,PC_CLK],
[0x100,INC_STACK],
[0x200,WR_STACK,D_Y],
[0x300,SIC_RST]])

# 0xA5 PUSH MEM_U
instr.append([[0xA5],
[0x000,S_MEZZ,PC_CLK],
[0x100,INC_STACK],
[0x200,WR_STACK,D_MEM_U],
[0x300,SIC_RST]])

# 0xA6 PUSH MEM_L
instr.append([[0xA6],
[0x000,S_MEZZ,PC_CLK],
[0x100,INC_STACK],
[0x200,WR_STACK,D_MEM_L],
[0x300,SIC_RST]])

# 0xA7 NOP (reserved)

# 0xA8 POP ACC
instr.append([[0xA8],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,S_ACC],
[0x200,SIC_RST]])

# 0xA9 POP X
instr.append([[0xA9],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,S_X],
[0x200,SIC_RST]])

# 0xAA POP Y
instr.append([[0xAA],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,S_Y],
[0x200,SIC_RST]])

# 0xAB POP MEM_U
instr.append([[0xAB],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,S_MEM_U],
[0x200,SIC_RST]])

# 0xAC POP MEM_L
instr.append([[0xAC],
[0x000,S_MEZZ,PC_CLK],
[0x100,DEC_STACK,S_MEM_L],
[0x200,SIC_RST]])

# -- snip --
# also SPL/SPU, SXL,SXU

# 0xC0 NOP (reserved)
# 0xC1 NOP (reserved)

# 0xC2 MOV ACC X
instr.append([[0xC2],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_ACC,D_X],
[0x200,SIC_RST]])

# 0xC3 MOV ACC Y
instr.append([[0xC3],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_ACC,D_Y],
[0x200,SIC_RST]])

# 0xC4 MOV ACC MEM_U
instr.append([[0xC4],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_ACC,D_MEM_U],
[0x200,SIC_RST]])

# 0xC5 MOV ACC MEM_L
instr.append([[0xC5],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_ACC,D_MEM_L],
[0x200,SIC_RST]])

# 0xC6 NOP (reserved)

# 0xC7 NOP (reserved)

# 0xC8 MOV X ACC
instr.append([[0xC8],
[0x000,S_MEZZ,PC_CLK],
[0x100,D_ACC,S_X],
[0x200,SIC_RST]])

# 0xC9 MOV X Y
instr.append([[0xC9],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_X,D_Y],
[0x200,SIC_RST]])

# 0xCA MOV X MEM_U
instr.append([[0xCA],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_X,D_MEM_U],
[0x200,SIC_RST]])

# 0xCB MOV X MEM_L
instr.append([[0xCB],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_X,D_MEM_L],
[0x200,SIC_RST]])

# 0xCC NOP (reserved)
# 0xCD NOP (reserved)

# 0xCE MOV Y ACC
instr.append([[0xCE],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_Y,D_ACC],
[0x200,SIC_RST]])

# 0xCF MOV Y X
instr.append([[0xCF],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_Y,D_X],
[0x200,SIC_RST]])

# 0xD0 MOV Y MEM_U
instr.append([[0xD0],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_Y,D_MEM_U],
[0x200,SIC_RST]])

# 0xD1 MOV Y MEM_L
instr.append([[0xD1],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_Y,D_MEM_L],
[0x200,SIC_RST]])

# 0xD2 NOP (reserved)
# 0xD3 NOP (reserved)

# 0xD4 MOV MEM_U ACC
instr.append([[0xD4],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_U,D_ACC],
[0x200,SIC_RST]])

# 0xD5 MOV MEM_U X
instr.append([[0xD5],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_U,D_X],
[0x200,SIC_RST]])

# 0xD6 MOV MEM_U Y
instr.append([[0xD6],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_U,D_Y],
[0x200,SIC_RST]])

# 0xD7 MOV MEM_U MEM_L
instr.append([[0xD7],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_U,D_MEM_L],
[0x200,SIC_RST]])

# 0xD8 NOP (reserved)
# 0xD9 NOP (reserved)

# 0xDA MOV MEM_L ACC
instr.append([[0xDA],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_L,D_ACC],
[0x200,SIC_RST]])

# 0xDB MOV MEM_L X
instr.append([[0xDB],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_L,D_X],
[0x200,SIC_RST]])

# 0xDC MOV MEM_L Y
instr.append([[0xDC],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_L,D_Y],
[0x200,SIC_RST]])

# 0xDD MOV MEM_L MEM_U
instr.append([[0xDD],
[0x000,S_MEZZ,PC_CLK],
[0x100,S_MEM_L,D_MEM_U],
[0x200,SIC_RST]])

# 0xDE AND imm
instr.append([[0xDE],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_ACC,ALU_AANDB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xDF NOP (reserved)

# 0xE0 NOP (reserved)

# 0xE1 AND X
instr.append([[0xE1],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_X,ALU_AANDB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE2 AND Y
instr.append([[0xE2],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_Y,ALU_AANDB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE3 OR imm
instr.append([[0xE3],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_ACC,ALU_AORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE4 OR X
instr.append([[0xE4],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_X,ALU_AORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE5 OR Y
instr.append([[0xE5],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_Y,ALU_AORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE6 XOR imm
instr.append([[0xE6],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,A_ACC,ALU_AXORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE7 XOR X
instr.append([[0xE7],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_X,ALU_AXORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE8 XOR Y
instr.append([[0xE8],
[0x000,S_MEZZ,PC_CLK],
[0x100,A_ACC,D_Y,ALU_AXORB,ALU_M,S_ALU],
[0x200,D_ALU,S_ACC],
[0x300,SIC_RST]])

# 0xE9 AND abs
instr.append([[0xE9],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_ACC,ALU_AANDB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xEA AND X abs
instr.append([[0xEA],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_X,ALU_AANDB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xEB AND Y abs
instr.append([[0xEB],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_Y,ALU_AANDB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xEC OR abs
instr.append([[0xEC],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_ACC,ALU_AORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xED OR X abs
instr.append([[0xED],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_X,ALU_AORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xEE OR Y abs
instr.append([[0xEE],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_Y,ALU_AORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xEF XOR abs
instr.append([[0xEF],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_ACC,ALU_AXORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xF0 XOR X
instr.append([[0xF0],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_X,ALU_AXORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xF1 XOR Y
instr.append([[0xF1],
[0x000,S_MEZZ,PC_CLK],
[0x100,PC_CLK,S_PC_U],
[0x200,PC_CLK,S_PC_L],
[0x300,ALT_MEM,A_Y,ALU_AXORB,ALU_M,S_ALU],
[0x400,D_ALU,S_ACC],
[0x500,SIC_RST]])

# 0xF2 NOP (reserved)
# 0xF3 NOP (reserved)
# 0xF4 NOP (reserved)
# 0xF5 NOP (reserved)
# 0xF6 NOP (reserved)
# 0xF7 NOP (reserved)
# 0xF8 NOP (reserved)
# 0xF9 NOP (reserved)
# 0xFA NOP (reserved)
# 0xFB NOP (reserved)
# 0xFC NOP (reserved)
# 0xFD NOP (reserved)
# 0xFE NOP (reserved)

# 0xFF NOP
instr.append([[0xFF],
[0x000,S_MEZZ,PC_CLK],				# Load opcode register
[0x100,SIC_RST]])					# Increment PC, SIC reset



mask = [0xFF, 0xFF, 0xFF]

# init rom lists:
rom0 = []
rom1 = []
rom2 = []

for x in range(0,2048):
	rom0.append(0)
	rom1.append(0)
	rom2.append(0)

for opcode in instr:
	# this will determine where in memory the instruction resides.
	# simulated opcode roms are 11-bit in, 8-bit out; each opcode regardless of actual executable length occupies 8 addresses.
	# thus, the instruction may be multiplied by 64 bits to get the offset for each instruction.
	# print "opcode: " + str(hex(opcode[0][0]))

	for subinstr in opcode[1:]:
		oldaction = [[0],[0],[0]]
		# this will generate a line for each sub instruction. the first value in the list is the sub-instruction address.
		# this address can be added to the opcode to generate the real rom location of the code.
		for action in subinstr[1:]:
			# each sub-instruction is composed of one or more actions. an action is the physical raising or lowering of logic levels
			# on the control lines which are internal to the CPU. These must be ANDed together to get the full sub instruction.
			oldaction = [[action[0][0] | oldaction[0][0]] ,[action[1][0] | oldaction[1][0]] ,[action[2][0] | oldaction[2][0]]]
			
		# print semi-formatted text strings (nearly acceptable for logisim now!!):
		# print hex(subinstr[0] + opcode[0][0])[2:] + ": " +  hex(oldaction[0][0])[2:] + " " + hex(oldaction[1][0])[2:] + " " + hex(oldaction[2][0])[2:]
		currentAddress = subinstr[0] + opcode[0][0]

		rom0[currentAddress] = oldaction[0][0]
		rom1[currentAddress] = oldaction[1][0]
		rom2[currentAddress] = oldaction[2][0]

bytecount = 0

# logisim format:


f0 = open('rom0.rom', 'w')
f1 = open('rom1.rom', 'w')
f2 = open('rom2.rom', 'w')

print "v2.0 raw"
f0.write("v2.0 raw\n")
f1.write("v2.0 raw\n")
f2.write("v2.0 raw\n")

for val in rom0:
	if bytecount == 8:
		bytecount = 0
		print "\n",
		f0.write("\n")

	bytecount += 1
	print hex(val)[2:],
	f0.write(hex(val)[2:] + " ")

for val in rom1:
	if bytecount == 8:
		bytecount = 0
		print "\n",
		f0.write("\n")

	bytecount += 1
	print hex(val)[2:],
	f1.write(hex(val)[2:] + " ")

for val in rom2:
	if bytecount == 8:
		bytecount = 0
		print "\n",
		f0.write("\n")

	bytecount += 1
	print hex(val)[2:],
	f2.write(hex(val)[2:] + " ")

