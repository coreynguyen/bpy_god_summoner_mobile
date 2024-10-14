/* -----------------------------------------------------------------------------------
	Title:        	God Summoner Mesh Importer
	Description:  	Imports models from God Summoner on the PC
	Release:       	December 27 2022 
	Author:       	mariokart64n
	
	Notes:
	# ------------------------------------------------------------------------------ #
		Unknown data between buffers could cause files to crach due reading in the
		the wrong place.
		normals and other data are unknown in the vertex data, therefore it isn't
		really possible to write models back - Dec 27 2022
		
		When I reviewed this topic in relation to the mesh format there was mention
		of the files being compressed by lzo1x.
			https://forum.xentax.com/viewtopic.php?f=16&t=21385
		
		No samples were provided, but I located some source code on lzo1x decoding.
			https://github.com/ARM-software/u-boot/blob/master/lib/lzo/lzo1x_decompress.c
		
		This other game 'Goddess of Genesis' may also have the same formats,
		but I was unable to secure file samples, links were down.
			https://forum.xentax.com/viewtopic.php?t=22942

	
	Change Log:
	# ------------------------------------------------------------------------------ #
	
	[2022-12-27]
		Wrote it!
	

*/ -----------------------------------------------------------------------------------


gc()
clearListener()

try(DestroyDialog ui_godsummoner)catch(ui_godsummoner)
rollout ui_godsummoner "God Summoner" (
	button btn1 "Import" width:120 height:30
	checkbox chk1 "Clear Scene" checked:true
	spinner spn1 "Scale" range:[-999999999.0, 999999999.0, 3.93701] type:#float scale:0.01 align:#left
	label lbl1 ""
	group "About" (
		hyperLink lb5 "Author: mariokart64n" address:"mailto:mario_kart64n@hotmail.com"
		label lb3 "Date: December 27 2022" align:#left
		)
	fn read_half &f = (
		local inputAsInt = readshort f #unsigned
		local sign = (bit.and (bit.shift inputAsInt -15) 0x00000001)
		local exponent = (bit.shift (bit.and inputAsInt 0x7C00) -10) as integer + 112
		local fraction = (bit.and inputAsInt 0x03FF)
		bit.intasfloat (
			(bit.or (bit.or (bit.shift fraction 13) (bit.shift exponent 23)) (bit.shift sign 31))
			)
		)
	
	fn write_half &s val = (
		local Sign = 0
		local exponent=0
		local Mantissa=0
		local Result = 0
		local Src = bit.floatAsInt (val as float)
		-- Extract sign, exponentonent, and mantissa from Single number
		Sign = bit.shift Src -31
		exponent = (bit.shift (bit.and Src 0x7F800000) -23) - 127 + 15
		Mantissa = bit.and Src 0x007FFFFF
		if exponent >= 0 and exponent <= 30 then (
			-- Simple case - round the significand and combine it with the sign and exponentonent
			Result = bit.or (bit.shift Sign 15) (bit.or (bit.shift exponent 10) (bit.shift (Mantissa + 0x00001000) -13))
			)
		else (
			if Src == 0 then (
				-- Input float is zero - return zero
				Result = 0
				)
			else (
				-- Difficult case - lengthy conversion
				if exponent <= 0 then (
					if exponent <= -10 then (         
						-- Input float's value is less than HalfMin, return zero
						Result = 0
						)
					else (
						-- Float is a normalized Single whose magnitude is less than HalfNormMin.  
						-- We convert it to denormalized half.
						Mantissa = bit.shift (bit.or Mantissa 0x00800000) -(1 - exponent)
						-- Round to nearest
						if (bit.or Mantissa 0x00001000) >= 0 then
						Mantissa = Mantissa + 0x00002000
						-- Assemble Sign and Mantissa (exponent is zero to get denormalized number)
						Result = bit.or (bit.shift Sign 15) (bit.shift Mantissa -13)
						)
					)
				else (
					if exponent = 255 - 127 + 15 then (
						if Mantissa = 0 then (
							-- Input float is infinity, create infinity half with original sign
							Result = (bit.shift Sign 15) or 0x7C00
							)
						else (
							-- Input float is NaN, create half NaN with original sign and mantissa
							Result = bit.or (bit.shift Sign 15) (bit.or 0x7C00 (bit.shift Mantissa -13))
							)
						)
					else (
						-- exponent is > 0 so input float is normalized Single
						-- Round to nearest
						if (bit.and Mantissa 0x00001000) >= 0 then (
							Mantissa = Mantissa + 0x00002000
							if (bit.and Mantissa 0x00800000) >= 0 then (
								Mantissa = 0
								exponent = exponent + 1
								)
							)
						if exponent >= 30 then (
							-- exponentonent overflow - return infinity half
							Result = (bit.shift Sign 15) or 0x7C00
							)
						else (
							-- Assemble normalized half
							Result = bit.or (bit.shift Sign 15) (bit.or (bit.shift exponent 10) (bit.shift Mantissa -13))
							)
						)
					)
				)
			)
		writeShort s result #unsigned
		)
	
	struct fmtSM2_Bone ( -- 36 Bytes or (32 bytes if in the SKIN file)
		/*char[4]*/  	name     = "",
		/*float[3]*/ 	position = [0.0, 0.0, 0.0],
		/*float[3]*/ 	rotation = (quat 0 0 0 1),
		/*uint16_t*/ 	unk006   = 0, -- Always 1?
		/*uint16_t*/ 	unk007   = 0, -- always 2928? flag?
		
		-- for SKIN file
		/*uint16_t*/    	boneid = -1,
		/*float[16]*/    	matrix = #(
			#(0.0, 0.0, 0.0, 0.0),
			#(0.0, 0.0, 0.0, 0.0),
			#(0.0, 0.0, 0.0, 0.0),
			#(0.0, 0.0, 0.0, 0.0)
			),
		
		fn asMat4x3 = (
			local r = matrix3 \
				([matrix[1][1], matrix[1][2], matrix[1][3]] + matrix[1][4]) \
				([matrix[2][1], matrix[2][2], matrix[2][3]] + matrix[2][4]) \
				([matrix[3][1], matrix[3][2], matrix[3][3]] + matrix[3][4]) \
				([matrix[4][1], matrix[4][2], matrix[4][3]] * matrix[4][4])
			r
			),
		
		fn read &f &type = (
			local i = 1
			local b = 1
			if type == 0x00534D32 then (
				name      = ""
				for i = 1 to 4 do (
					b = readByte f #unsigned
					if b > 0 do (name += bit.IntAsChar(b))
					)
				position = [readFloat f, readFloat f, readFloat f]
				rotation = (quat (readFloat f) (readFloat f) (readFloat f) (readFloat f))
				unk006   = readShort f #unsigned
				unk007   = readShort f #unsigned
				
				-- patch to SKI2
				boneid = -1
				local m = rotation as matrix3
				matrix = #(
					#(m.row1.x, m.row1.y, m.row1.z, 0.0),
					#(m.row2.x, m.row2.y, m.row2.z, 0.0),
					#(m.row3.x, m.row3.y, m.row3.z, 0.0),
					#(position.x, position.y, position.z, 1.0)
					)
				)
			else if type == 0x534B4932 then (
				boneid = readShort f #unsigned
				matrix = #(
					#(read_half f, read_half f, read_half f, read_half f),
					#(read_half f, read_half f, read_half f, read_half f),
					#(read_half f, read_half f, read_half f, read_half f),
					#(read_half f, read_half f, read_half f, read_half f)
					)
				
				-- Patch to SM file
				name = "Bone " + (boneid as string)
				position = [matrix[4][1], matrix[4][2], matrix[4][3]] * matrix[4][4]
				local r = asMat4x3()
				rotation = r.rotation
				)
			),
		
		fn write &s type = (
			if type == 0x00534D32 then (
				local i = 1
				local b = 1
				local name_len = name.count
				for i = 1 to 4 do (
					b = 0
					if i <= name_len do (b = bit.CharAsInt(subString name i 1))
					writeByte s b #unsigned
					)
				for i = 1 to 3 do (writeFloat s position[i])
				writeFloat s rotation.x
				writeFloat s rotation.y
				writeFloat s rotation.z
				writeFloat s rotation.w
				writeShort s unk006 #unsigned
				writeShort s unk007 #unsigned
				)
			else if type == 0x534B4932 then (
				writeShort s boneid #unsigned
				local i = 1
				local j = 1
				for i = 1 to 4 do (for j = 1 to 4 do (write_half &s matrix[i][j]))
				)
			)
		
		)
	
	struct fmtSKEL_Hierarchy ( -- 12 Bytes
		/*uint32_t*/ 	index = -1,
		/*uint32_t*/ 	parent = -1,
		/*uint32_t*/ 	unk017 = 0,
		
		fn read &f = (
			index = readLong f #signed
			parent = readLong f #signed
			unk017 = readLong f #signed
			),
		
		fn write &s = (
			writeLong s index #signed
			writeLong s parent #signed
			writeLong s unk017 #signed
			)
		
		)
	
	struct fmtSKEL ( -- 24 Bytes + n Bytes (bone info)
		/*char[4]*/  	type = "",
		/*uint16_t*/ 	unk010 = 0,
		/*uint32_t*/ 	unk011 = 0,
		/*float*/    	unk012 = 0,
		/*uint32_t*/ 	num_bones = 0,
		/*string[n]*/	names = #(),
		/*uint32_t*/ 	unk013 = 0,
		/*uint32_t*/ 	unk014 = 0,
		/*Hierarchy[n]*/parents = #(),
		
		fn name index = (
			local n = ""
			if index > -1 do (
				local i = 1
				for i = 1 to parents.count do (
					if index == parents[i].index and i <= names.count do (
						n = names[i]
						exit
						)
					)
				)
			n
			),
		
		fn parent index = (
			local par = -1
			if index > -1 do (
				local i = fmtSKEL_Hierarchy()
				for i in parents do (
					if index == i.index do (
						par = i.parent
						exit
						)
					)
				)
			par
			),
		
		fn size = (
			local nsize = 32 + (parents.count * 12)
			nsize
			),
		
		fn readFixedString &f len = (
			local s = "", i = 1, b = 0, p = ftell f + len
			for i = 1 to len do (
				b = readByte f #unsigned
				if b == 0 do (exit)
				s += bit.IntAsChar(b)
				)
			fseek f p #seek_set
			s
			),
		
		fn read &f = (
			local b = 1
			local i = 1
			type = ""
			for i = 1 to 5 do (
				b = readShort f #unsigned
				if b > 0 do (type += bit.IntAsChar(b))
				)
			if type == "SKEL" then (
				unk010 = readShort f #unsigned
				unk011 = readLong f #unsigned
				unk012 = readFloat f
				num_bones = readLong f #unsigned
				names = #()
				parents = #()
				format "num_bones: \t%\n" num_bones
				if num_bones > 0 do (
					local i = 1
					names[num_bones] = ""
					parents[num_bones] = fmtSKEL_Hierarchy()
					for i = 1 to num_bones do (
						names[i] = readFixedString &f (readLong f #unsigned)
						)
					unk013 = readLong f #unsigned
					unk014 = readLong f #unsigned
					for i = 1 to num_bones do (
						parents[i] = fmtSKEL_Hierarchy()
						parents[i].read(&f)
						)
					)
					
				) else (format "Error: \tInvalid File Type {%}\n" type)
			),
		
		fn write &s = (
			local i = 1
			for i in #(0x53, 0x4B, 0x45, 0x4C, 0x00) do (writeShort s i #unsigned)
			writeShort s unk010 #unsigned
			writeLong s unk011 #unsigned
			writeFloat s unk012
			num_bones = parents.count
			writeLong s num_bones #unsigned
			for i = 1 to num_bones do (
				if i <= names.count then (
					writeLong s (names[i].count + 1) #unsigned
					writeString s names[i]
					) else (writeLong s 0 #unsigned)
				)
			writeLong s unk013 #unsigned
			writeLong s unk014 #unsigned
			for i = 1 to num_bones do (parents[i].write(&s))
			),
		
		fn open file = (
			local result = false
			if file != undefined and file != "" do (
				local f = try(fopen file "rb")catch(undefined)
				if f != undefined then (
					read(&f)
					fclose f
					result = true
					) else (format "Error: \tFailed to open file {%}\n" file)
				)
			result
			),
		
		fn save file = (
			local result = false
			if file != undefined and file != "" do (
				local s = try(fopen file "wb")catch(undefined)
				if s != undefined then (
					write(&s)
					fclose s
					result = true
					) else (format "Error: \tFailed to save file {%}\n" file)
				)
			result
			)
		
		)
	
	struct fmtSM2_Skeleton ( --  4 Bytes + n bytes (Bone Data)
		/*uint32_t*/ 	num_bones = 0,
		/*Bone[n]*/  	bones = #(),
		
		-- for SKEL file
		/*fmtSKEL*/  	skel = fmtSKEL(),
		fn size &type = (
			local nsize = 4
			if type == 0x00534D32 then (nsize += bones.count * 36)
			else if type == 0x534B4932 then (nsize += bones.count * 32)
			nsize
			),
		
		fn read &f &type = (
			num_bones = readLong f #unsigned
			bones = #()
			if num_bones > 0 do (
				bones[num_bones] = fmtSM2_Bone()
				local i = 1
				for i = 1 to num_bones do (
					bones[i] = fmtSM2_Bone()
					bones[i].read &f type
					)
				)
			),
		
		fn write &s = (
			num_bones = bones.count
			writeLong s num_bones #unsigned
			local i = 1
			for i = 1 to num_bones do (
				bones[i].write &s type
				)
			)
		
		)

	struct fmtSM2_FaceBuf ( -- 4 Bytes + n bytes (faces indices)
		/*uint32_t*/    	num_faces = 0,
		/*uint16_t[3]*/ 	faces     = #(),
		
		fn size = (
			nsize = 4 + (faces.count * 3 * 2)
			nsize
			),
		
		fn read &f base:1 = (
			result = false
			num_faces = readLong f #unsigned
			faces = #()
			if num_faces > 0 do (
				faces[num_faces] = [1, 1, 1]
				local i = 1
				for i = 1 to num_faces do (
					faces[i] = [readShort f #unsigned, readShort f #unsigned, readShort f #unsigned] + base
					--faces[i] = [faces[i][1], faces[i][3], faces[i][2]]
					)
				result = true
				)
			result
			),
		
		fn write &s base:1 = (
			local i = 1
			local v = 1
			num_faces = faces.count
			writeLong s num_faces #unsigned
			for i = 1 to num_faces do (
				for v = 1 to 3 do (
					--faces[i] = [faces[i][1], faces[i][3], faces[i][2]]
					writeShort s (faces[i][v] - base) #unsigned
					)
				)
			result = true
			)
		
		)

	struct fmtSM2_Object (
		/*uint32_t*/ 	name_len  = 0,
		/*char[n]*/  	name      = "",
		/*uint16_t*/ 	unk003    = 0, -- ?? padding ??? insufficient samples to determine
		/*uint32_t*/ 	max_index = 0, -- same as vertex count from header
		/*uint8_t*/  	unk004    = 0, -- ?? padding ??? insufficient samples to determine
		/*float[3]*/ 	bb_max    = [0.0, 0.0, 0.0], -- same as in header
		/*float[3]*/ 	bb_min    = [0.0, 0.0, 0.0], -- same as in header
		/*FaceBuf[n]*/ 	faceBuf   = #(), -- no count? read until end is reached
		/*uint32_t*/ 	unk005    = 0, -- ?? padding ??? insufficient samples to determine
		/*
			its unknown how this block terminates, and theres not enough samples to
			investigate..
			I assume that when a 4byte null is reached the read is terminated
			
			however the padding afterwards seems to vary in sample
		*/
		/*uint32_t*/ 	padding   = 0,
		
		fn size = (
			local nsize = 46 + padding + name.count
			local i = 1
			for i = 1 to faceBuf.count do (
				nsize += faceBuf[i].size()
				)
			nsize
			),
		
		fn seekPastWhiteSpace &f len:16 = (
			/*
				this is a hack to skip and 0's or padding after the face buffer
			*/
			local i = 1
			local b = 1
			local p = ftell f
			for i = 1 to len do (
				b = readByte f #unsigned
				if b > 0 or b == undefined do (
					fseek f -1 #seek_cur
					exit
					)
				)
			-- return number of bytes skipped
			(ftell f) - p
			),
		
		fn read &f stopAddr = (
			local i = 1
			local b = 1
			name_len  = readLong f #unsigned
			name      = ""
			for i = 1 to name_len do (
				b = readByte f #unsigned
				if b > 0 do (name += bit.IntAsChar(b))
				)
			unk003    = readShort f #unsigned
			max_index = readLong f #unsigned
			unk004    = readByte f #unsigned
			bb_max    = [readFloat f, readFloat f, readFloat f]
			bb_min    = [readFloat f, readFloat f, readFloat f]
			faceBuf   = #()
			local fb = fmtSM2_FaceBuf()
			while ftell f < stopAddr do (
				fb = fmtSM2_FaceBuf()
				if not (fb.read(&f)) do exit
				append faceBuf fb
				)
			unk005    = readLong f #unsigned
			
			-- Unsure how the padding in this area works, skip until a none 0 is reached
			padding = seekPastWhiteSpace(&f)
			format "padding: \t% (@ %)\n" padding ((ftell f) as integer)
			),
		
		fn write &s = (
			local i = 1
			name_len  = name.count + 1
			writeLong s name_len #unsigned
			writeString s name
			writeShort s unk003 #unsigned
			writeLong s max_index #unsigned
			writeByte s unk004 #unsigned
			for i = 1 to 3 do (writeFloat s bb_max[i])
			for i = 1 to 3 do (writeFloat s bb_min[i])
			for i = 1 to faceBuf.count do (faceBuf[i].write(&s))
			writeLong s 0 #unsigned
			writeLong s unk005 #unsigned
			for i = 1 to padding do (writeByte s 0 #unsigned)
			)
		
		)

	struct fmtSM2_Vertex ( -- 20 Bytes
		/*
			I'm unable to decode the normals and what could be also be bi-normals
			writing new geometry back to the file is therefore not possible or advise.
		*/
		
		/*float[3]*/ 	position  = [0.0, 0.0, 0.0],
		/*float[2]*/ 	texcorrd  = [0.0, 0.0, 0.0],
		/*float[4]*/ 	weight    = #(1.0, 0.0, 0.0, 0.0),
		/*uint8_t[4]*/ 	normal    = #(0.0, 0.0, 0.0, 0.0),
		/*uint8_t[4]*/ 	boneid    = #(-1, 0, 0, 0),
		/*uint8_t[4]*/ 	binormal  = #(0.0, 0.0, 0.0, 0.0),
		
		fn read &f &type = (
			position   = ([read_half f, read_half f, read_half f] + (read_half f))
			texcorrd   = [read_half f, 1.0 - (read_half f), 0.0]
			local i = 1
			case type of (
				0x00534D32: ( -- 'SM2' 20 Bytes
					normal = #(readByte f #unsigned, readByte f #unsigned, readByte f #unsigned, readByte f #unsigned) -- normal?
					binormal = #(readByte f #unsigned, readByte f #unsigned, readByte f #unsigned, readByte f #unsigned) -- tangent?
					)
				0x534B4932: ( -- 'SKI2' 32 Bytes
					weight = #(read_half f, read_half f, read_half f, read_half f) -- weight
					normal = #(readByte f #unsigned, readByte f #unsigned, readByte f #unsigned, readByte f #unsigned) -- normal?
					boneid = #(readByte f #unsigned, readByte f #unsigned, readByte f #unsigned, readByte f #unsigned) -- boneid
					binormal = #(readByte f #unsigned, readByte f #unsigned, readByte f #unsigned, readByte f #unsigned) -- tangent?
					-- round off the weights, theres some issues with the half float function
					for i = 1 to weight.count do (weight[i] = ((weight[i] * 1000) as integer) / 1000.0)
					)
				)
			),
		
		fn write &s = (
			local i = 1
			for i = 1 to 3 do (write_half s position[i])
			texcorrd = [texcorrd[1], 1.0 - texcorrd[1], 0.0]
			for i = 1 to 2 do (write_half s texcorrd[i])
			for i = 1 to 4 do (writeShort s (unk009[i]) #unsigned)
			)
		
		)
	
	struct fmtSM2 ( -- 60 Bytes + n Bytes (Buffers)
		/*uint32_t*/ 	type       = 0x00534D32, -- SM2, SKI2
		/*uint32_t*/ 	version    = 0x0105011B,
		/*uint32_t*/ 	num_verts  = 0,
		/*float[3]*/ 	bb_min     = [0.0, 0.0, 0.0],
		/*float[3]*/ 	bb_max     = [0.0, 0.0, 0.0],
		/*float*/    	draw_dist  = [0.0, 0.0, 0.0],
		/*uint32_t*/ 	unk001     = 0, -- Padding?
		/*uint32_t*/ 	unk002     = 0, -- Padding?
		/*uint32_t*/ 	verts_addr = 0,
		/*uint32_t*/ 	meshs_addr = 0,
		/*uint32_t*/ 	bones_addr = 0,
		/*Vertex*/   	verts = #(),
		/*Object*/  	meshs = fmtSM2_Object(),
		/*Skeleton*/ 	bones = fmtSM2_Skeleton(),
		
		fn size type = (
			local nsize = 52
			if type == 0x00534D32 then (
				nsize += 8 + (verts.count * 20) + (meshs.size()) + (bones.size())
				)
			else (
				nsize += 8 + (verts.count * 32) + (meshs.size()) + (bones.size(type))
				)
			nsize
			),
		
		fn read &f skelfile:"" = (
			local pos = ftell f
			fseek f 0 #seek_end
			local fsize = ftell f
			local result = false
			local i = 1
			
			fseek f pos #seek_set
			
			if fsize > 52 then (
				type = readLong f #unsigned
				if type == 0x00534D32 or type == 0x534B4932 then (
					version    = readLong f #unsigned
					if type == 0x00534D32 then (
						num_verts  = readLong f #unsigned
						)
					else if type == 0x534B4932 then (
						num_verts  = readShort f #unsigned
						verts_addr = readShort f #unsigned
						)
					bb_min     = [readFloat f, readFloat f, readFloat f]
					bb_max     = [readFloat f, readFloat f, readFloat f]
					draw_dist  = readFloat f
					if type == 0x00534D32 do (
						unk001     = readLong f #unsigned
						unk002     = readLong f #unsigned
						verts_addr = readLong f #unsigned
						)
					meshs_addr = readLong f #unsigned
					bones_addr = readLong f #unsigned
					
					verts = #()
					if verts_addr > 0 and num_verts > 0 do (
						verts[num_verts] = fmtSM2_Vertex()
						fseek f verts_addr #seek_set
						for i = 1 to num_verts do (
							verts[i] = fmtSM2_Vertex()
							verts[i].read &f type
							)
						)
					
					if type == 0x534B4932 do (meshs_addr = ftell f)
					
					meshs = #()
					if meshs_addr > 0 and meshs_addr < fsize do (
						fseek f meshs_addr #seek_set
						meshs = fmtSM2_Object()
						meshs.read &f fsize
						)
					
					if type == 0x534B4932 do (bones_addr = ftell f)
					format "bones_addr: \t%\n" bones_addr
					
					bones = #()
					if bones_addr > 0 and bones_addr < fsize do (
						fseek f bones_addr #seek_set
						bones = fmtSM2_Skeleton()
						bones.read &f type
						
						if type == 0x534B4932 and skelfile != undefined and skelfile != "" and doesFileExist skelfile do (
							if not bones.skel.open(skelfile) do (
								format "Warning: \tFailed to locate SKEL file\n"
								)
							)
						)
					result = true
					) else (format "Error: \tUnsupported File Type (0x)\n" (bit.IntAsHex (type as integer)))
				) else (format "Error: \tInvalid File Size {%}\n" fsize)
			result
			),
		
		fn write &s = (
			local i = 1
			local ptr = 60 -- Vertex Buffer Position, Always 60
			num_verts = verts.count
			writeLong s 0x00534D32 #unsigned -- 'SM2'
			writeLong s version #unsigned
			writeLong s num_verts #unsigned
			for i = 1 to 3 do (writeFloat s bb_min[i])
			for i = 1 to 3 do (writeFloat s bb_max[i])
			writeFloat s draw_dist
			writeLong s unk001 #unsigned
			writeLong s unk002 #unsigned
			writeLong s ptr #unsigned -- Vertices Address
			ptr += num_verts * 20
			writeLong s ptr #unsigned -- Objects Address
			ptr += meshs.size()
			writeLong s ptr #unsigned -- Bones Address
			for i = 1 to num_verts do (verts[i].write(&s))
			meshs.write(s)
			bones.write(s)
			),
		
		fn build texName:"" mscale:0.1 rotOff:(matrix3 [-1,0,0] [0,0,1] [0,1,0] [0,0,0]) = (
			
			-- ClearScene
			delete $*
			
			-- Build Skeleton
			local boneArray = #()
			local b = undefined
			local i = 1
			local bs = 2.0
			local n = ""
			local p = -1
			for i = 1 to bones.num_bones do (
				b = bonesys.createbone (bones.bones[i].position * mscale) ((bones.bones[i].position + [0.0, 0.4, 0.0]) * mscale) [0, 1, 0]
				b.name=bones.bones[i].name
				b.position=bones.bones[i].position * mscale
				b.rotation=bones.bones[i].rotation
				b.width = b.height = 1.5
				b.showLinks = b.showLinksOnly = true
				--b.boneEnable=false
				b.transform = (inverse (bones.bones[i].asMat4x3())) * rotOff
				b.position *= mscale
				b.position.x = -b.position.x
				n = bones.skel.name(bones.bones[i].boneid)
				if n != "" do (b.name = n)
				append boneArray b
				)
			local j = 1
			for i = 1 to boneArray.count do (
				p = bones.skel.parent(bones.bones[i].boneid)
				if p > -1 do (
					for j = 1 to bones.num_bones do (
						if bones.bones[j].boneid == p do (
							boneArray[i].parent = boneArray[j]
							exit
							)
						)
					)
				)
			
			-- Build Meshes
			local vertArray = #()
			local tvertArray = #()
			if verts.count > 0 do (
				vertArray[verts.count] = [0.0, 0.0, 0.0]
				tvertArray[verts.count] = [0.0, 0.0, 0.0]
				for i = 1 to verts.count do (
					vertArray[i] = [verts[i].position[1], verts[i].position[3], verts[i].position[2]] * mscale
					tvertArray[i] = [verts[i].texcorrd[1], verts[i].texcorrd[2], 0.0]
					)
				)
			
			local msh = undefined
			local v = 1
			for i = 1 to meshs.faceBuf.count do ( -- these appear to be Level of Details meshes
				if meshs.faceBuf[i].faces.count == 0 do continue
				msh = mesh vertices:vertArray faces:meshs.faceBuf[i].faces tverts:tvertArray
				if meshs.name != "" do (msh.name = meshs.name + " (" + (i as string) + ")")
				msh.numTVerts = tvertArray.count
				msh.displayByLayer = false
				msh.backfacecull = on
				buildTVFaces msh
				for v = 1 to tvertArray.count do (setTVert msh v tvertArray[v])
				for v = 1 to meshs.faceBuf[i].faces.count do setTVFace msh v meshs.faceBuf[i].faces[v]
				for v = 1 to meshs.faceBuf[i].faces.count do (setFaceSmoothGroup msh v 0)
				if texName != "" do (
					msh.material = StandardMaterial diffuseMap:(Bitmaptexture fileName:texName)
					showTextureMap msh.material on
					)
				
				if i > 1 do (hide msh)
				
				
				-- Import Weights
				local weights = #()
				local boneids = #()
				if boneArray.count > 0 do (
					
					max modify mode
					
					-- Create Skin Modifier
					local skinMod = skin()
					
					
					-- Add Modifier to objecy
					select msh
					addModifier msh skinMod
					
					
					-- Add bones to modifier
					local vi = 1
					local bu = 0
					for vi = 1 to boneArray.count do (
						if vi == boneArray.count do (bu = 1)
						skinOps.addbone skinMod boneArray[vi] bu
						)
					
					-- Update Mesh
					update msh
					
					-- Get Number of Bones in Skin Modifier
					local boneListCount = skinOps.GetNumberBones skinMod
					
					-- Build Bone List Map
					local boneMap = #()
					local nodeName = ""
					local fi = 1
					if boneListCount > 0 do (
						
						-- dimension bone map
						boneMap[boneListCount] = 1
						
						-- Search for Bone Id in boneArray (Array with all the bones)
						for vi = 1 to boneListCount do (
							-- Initialize Bone Map to 1st bone
							boneMap[vi] = 1
							
							-- get bone name from skin modifier list
							nodeName = skinOps.GetBoneName skinMod vi 0
							
							-- search bonearray
							for fi = 1 to boneArray.count do (
								-- if bone name is found, assign to bone map
								
								if boneArray[fi].name == nodeName do (
									boneMap[vi] = fi
									)
								)
							)
						)
					
					-- apply weights to skin modifier
					modPanel.setCurrentObject skinMod
					local bi = #()
					local we = #()
					for vi = 1 to verts.count do (
						bi = #()
						we = #()
						
						for fi = 1 to verts[vi].weight.count do (
							if verts[vi].weight[fi] > 0.0 do (
								x = findItem boneMap (verts[vi].boneid[fi] + 1)
								if x > 0 do (
									append bi x
									append we verts[vi].weight[fi]
									)
								)
							)
						skinOps.ReplaceVertexWeights skinMod vi bi we
						)
					
					if skinOps.isWeightToolOpen skinMod == 0 do (
						skinOps.WeightTool skinMod
						)
					
					skinMod.filter_vertices = on
					)
				
				
				)
			
			
			
			
			)
		
		)
	
	local sm = fmtSM2()
	
	fn read file clear_scene:true mscale:0.1 = (
		if file != undefined and file != "" do (
			local fext = getFilenameType file
			
			if matchPattern fext pattern:".sm" or matchPattern fext pattern:".skin" then (
				local f = try(fopen file "rb")catch(undefined)
				if f != undefined then (
					local fpath = getFilenamePath file
					local fname = getFilenameFile file
					local skel_file = fpath + fname + ".skel"
					local mapd_file = fpath + fname + ".dds"
					if not doesFileExist skel_file do (
						local file = ""
						local files = getFiles (fpath + "*.skel")
						for file in files do (
							skel_file = file
							exit
							)
						)
					if not doesFileExist mapd_file do (
						local file = ""
						local files = getFiles (fpath + "*.dds")
						for file in files do (
							mapd_file = file
							exit
							)
						)
					
					sm = fmtSM2()
					sm.read &f skelfile:skel_file
					if clear_scene do (delete objects)
					sm.build texName:mapd_file mscale:mscale
					
					fclose f
					) else (format "failed to open file {%}\n" file)
				) else (format "file extension not supported {%}\n" fext)
			)
		)
	
	fn write file = (
		if file != undefined and file != "" and sm != undefined do (
			local fext = getFilenameType file
			if matchPattern fext pattern:".sm" then (
				local s = try(fopen file "wb")catch(undefined)
				if s != undefined then (
					
					sm.write(&s)
					
					fclose s
					) else (format "failed to save file {%}\n" file)
				) else (format "file extension not supported {%}\n" fext)
			)
		)
	
	on btn1 pressed do (
		
		read (
			GetOpenFileName caption:"Select Mesh File" types: "Mesh (*.sm)|*.sm;*.skin*.skel|All files (*.*)|*.*|"
			) clear_scene:chk1.checked mscale:spn1.value
		)
	)
CreateDialog ui_godsummoner
/*
ui_godsummoner.read (
	"E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\GodSummoner\\samples .skin .skel .sm\\wep\\bs06.sm"
	"E:\\BackUp\\MyCloud4100\\Coding\\Maxscripts\\File IO\\GodSummoner\\samples .skin .skel .sm\\npc\\mb35_obj1.skin"
-- 	"C:\\Users\\Corey\\Downloads\\Blender249[GodSummoner][sm][skin][skel][2019-11-22]\\samples .skin .skel .sm\\npc\\mb35_obj2.skin"
-- 	"C:\\Users\\Corey\\Downloads\\Blender249[GodSummoner][sm][skin][skel][2019-11-22]\\samples .skin .skel .sm\\npc\\common.skel"
	
	)
*/