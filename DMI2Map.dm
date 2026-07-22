// FPS does not speed up icon conversion; it only affects client tick rate.

world
	fps = 100
	view = 16

	New()
		var/list/letters = splittext("a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z",",")
		for(var/x in letters)
			alphabet += x

		for(var/x in letters)
			alphabet += uppertext(x)

		//outdoorTilesets = new('frontierOutdoor.dmi')
		//indoorTilesets = new('hginteriortilesets.dmi')
		fps = 240
		return ..()
client
	fps = 100

	New()
		. = ..()
		src << "========================================"
		src << "DMI2Map — how to use"
		src << "========================================"
		src << "1) Put map .png files under PNG/  (folders ok)"
		src << "2) Right-click yourself -> SetTileset"
		src << "   - Create New, or pick one from Tilesets/"
		src << "3) Right-click yourself -> ConvertPNG"
		src << "   - PNG -> 2x size .dmi in DMI/ -> then map convert"
		src << "   - Or ConvertPNG_Duplicates to force new tiles"
		src << "4) Already have .dmi? Use ConvertDMI / ConvertDMI_Duplicates"
		src << "5) Watch the numbered progress lines while it runs"
		src << "6) Maps/ = output maps  |  DMI/ = scaled icons  |  Tilesets/ = tileset"
		src << "========================================"
		src << "Flow: PNG -> 2x DMI -> split tiles -> map tiles -> write .dmm -> save tileset"
		src << "========================================"

var/list
	alphabet = list()
	tilesetSigs = list() // signature -> list of tileset icon_state names
// tileset is 8x92

var/tilesetName
var/icon/tileset
var/tilesetCount = 0

proc/compareIcon(var/icon/a,var/icon/b,var/state1,var/state2) // Assumes that both icons are same dimensions
	var/h = a.Height()
	var/w = a.Width()

	for(var/i = 1, i <= w, i++)
		for(var/j = 1, j <= h, j++)
			if( a.GetPixel(i,j,state1) != b.GetPixel(i,j,state2) )	return 0

	return 1

proc/iconSignature(var/icon/a, var/state)
	var/w = a.Width()
	var/h = a.Height()
	var/cx = max(1, round(w / 2))
	var/cy = max(1, round(h / 2))
	return "[a.GetPixel(1,1,state)]_[a.GetPixel(w,1,state)]_[a.GetPixel(1,h,state)]_[a.GetPixel(w,h,state)]_[a.GetPixel(cx,cy,state)]_[w]_[h]"

proc/indexTilesetState(var/state)
	var/sig = iconSignature(tileset, state)
	var/list/bucket = tilesetSigs[sig]
	if(!bucket)
		bucket = list()
		tilesetSigs[sig] = bucket
	bucket += state

proc/rebuildTilesetIndex()
	tilesetSigs = list()
	tilesetCount = 0
	if(!tileset) return
	for(var/s in tileset.IconStates())
		tilesetCount++
		indexTilesetState(s)

proc/findDuplicate(var/state,var/icon/a,var/icon/b) // returns matching icon_state from tileset, or 0
	var/sig = iconSignature(a, state)
	var/list/bucket = tilesetSigs[sig]
	if(bucket)
		for(var/x in bucket)
			if(compareIcon(a, b, state, x)) return x
	return 0


proc/isFolder(var/t)
	return copytext(t,length(t)) == "/"

proc/isDMI(var/t)
	return findtext(t,".dmi")

proc/isPNG(var/t)
	return findtext(t,".png") || findtext(t,".PNG")

proc/ensureFolder(var/path)
	if(!path) return
	if(copytext(path, length(path)) != "/")
		path = "[path]/"
	if(fexists(path)) return
	var/win = replacetext(copytext(path, 1, length(path)), "/", "\\")
	shell("cmd /c mkdir \"[win]\"")

// Load PNG as icon, copy, then Scale to 2x (BYOND pattern: icon() -> Scale -> fcopy).
proc/scaleIcon2x(var/icon/src_icon)
	var/w = src_icon.Width()
	var/h = src_icon.Height()
	var/icon/out = icon(src_icon)
	out.Scale(w * 2, h * 2)
	return out

// PNG/foo/bar.png -> DMI/foo/bar.dmi (doubled). Returns dest path.
proc/png_to_scaled_dmi(var/pngPath)
	var/rel = copytext(pngPath, length("PNG/") + 1) // after PNG/
	var/dot = findlasttext(rel, ".")
	if(!dot) return null
	var/dest = "DMI/[copytext(rel, 1, dot)].dmi"
	var/slash = findlasttext(dest, "/")
	if(slash)
		ensureFolder(copytext(dest, 1, slash))
	var/icon/img = icon(file(pngPath))
	if(!img || !img.Width() || !img.Height())
		return null
	var/icon/scaled = scaleIcon2x(img)
	fcopy(scaled, dest)
	return dest

proc/pngScaledSizeText(var/pngPath)
	var/icon/img = icon(file(pngPath))
	if(!img) return "?"
	return "[img.Width()]x[img.Height()] -> [img.Width() * 2]x[img.Height() * 2]"

proc/saveTileset()
	fcopy(tileset,"Tilesets/[tilesetName]")
	world << "Tileset [tilesetName] saved ( [tilesetCount] states )."

client/verb
	SetTileset()
		if(tileset)
			switch(alert(src,"There is currently a tileset set, are you sure you would like to change it?","Change Tileset","Yes","No"))
				if("No")	return
		var/list/tileFolder = list("Create New Tileset")
		tileFolder += flist("Tilesets/")

		var/t = input("Select a tileset.") as null |anything in tileFolder

		if(!t) return

		if(t == "Create New Tileset")
			var/n = input("Name of tileset?") as text |null
			if(n)
				tilesetName = "[n].dmi"
				tileset = new()
				rebuildTilesetIndex()
			else
				return
		else
			tileset = new(file("Tilesets/[t]"))
			tilesetName = t
			rebuildTilesetIndex()

		src << "Set tileset to [tilesetName] ( [tilesetCount] states )."



client/verb
	ConvertPNG()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/pngFolder = flist("PNG/")

		if(pngFolder.len)
			var/png = input("Select PNG to convert (2x -> DMI -> map).") as null | anything in pngFolder
			if(png)
				world << "=== ConvertPNG start (reuse duplicates) ==="
				recursiveConvertPNG("PNG/[png]")
				world << "=== Finished batch ==="
				saveTileset()
			else
				world << "Convert cancelled."
		else
			world << "Error: PNG/ folder is empty. Put .png maps there first."

client/verb
	ConvertPNG_Duplicates()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/pngFolder = flist("PNG/")

		if(pngFolder.len)
			var/png = input("Select PNG to convert (2x -> DMI -> map).") as null | anything in pngFolder
			if(png)
				world << "=== ConvertPNG start (always new tiles) ==="
				recursiveConvertPNG("PNG/[png]",1)
				world << "=== Finished batch ==="
				saveTileset()
			else
				world << "Convert cancelled."
		else
			world << "Error: PNG/ folder is empty. Put .png maps there first."

client/verb
	ConvertDMI()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/dmiFolder = flist("DMI/")

		if(dmiFolder.len)
			var/dmi = input("Select to convert.") as null | anything in dmiFolder
			if(dmi)
				world << "=== Convert start (reuse duplicates) ==="
				recursiveConvert("DMI/[dmi]")
				world << "=== Finished batch ==="
				saveTileset()
			else
				world << "Convert cancelled."
		else
			world << "Error: DMI/ folder is empty."

client/verb
	ConvertDMI_Duplicates()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/dmiFolder = flist("DMI/")

		if(dmiFolder.len)
			var/dmi = input("Select to convert.") as null | anything in dmiFolder
			if(dmi)
				world << "=== Convert start (always new tiles) ==="
				recursiveConvert("DMI/[dmi]",1)
				world << "=== Finished batch ==="
				saveTileset()
			else
				world << "Convert cancelled."
		else
			world << "Error: DMI/ folder is empty."

client/proc
	recursiveConvertPNG(t,d=0)

		if(isPNG(t))
			src << "=== Convert: [t] ==="
			src << "\[1/5] PNG -> 2x DMI..."
			var/dmiPath = png_to_scaled_dmi(t)
			if(!dmiPath)
				src << "Error: failed to convert [t]"
				return
			var/icon/check = new(file(dmiPath))
			src << "  saved [dmiPath] ([pngScaledSizeText(t)] -> [check.Width()]x[check.Height()])"
			recursiveConvert(dmiPath, d, 1) // from_png = 1 -> steps 2-5
			return

		if(isFolder(t))
			for(var/f in flist(t))
				recursiveConvertPNG("[t][f]",d)
			return

client/proc
	recursiveConvert(t,d=0,from_png=0) // t can also be considered a destination

		if(isDMI(t))
			var/point = findlasttext(t,"/")+1
			var/dmiFile = copytext(t,point)
			var/dmiFolder = copytext(t,1,point)

			if(!from_png)
				src << "=== Convert: [t] ==="
			var/fixStep = from_png ? "\[2/5]" : "\[1/4]"
			src << "[fixStep] Fixing DMI (splitting tiles)..."
			var/icon/map = new(file("[dmiFolder][dmiFile]"))
			dmi_to_map(FixDMI(map),dmiFolder,dmiFile,d,from_png)
			return

		if(isFolder(t))
			for(var/f in flist(t))
				recursiveConvert("[t][f]",d,from_png)
			return

client/proc
	dmi_to_map(icon/map,folder,fileName,d=0,from_png=0)

		var/list/iconStates = map.IconStates()
		var/lastState = iconStates[iconStates.len]
		var/totalTiles = iconStates.len

		var/maxX = text2num( splittext(lastState,",")[1] ) + 1
		//var/maxY = text2num( splittext(lastState,",")[2] ) + 1
		var/map_text = ""
		var/curX=1
		var/curY=1
		var/list/tilePosList = list()
		var/list/keyByTileId = list()
		var/reused = 0
		var/added = 0
		var/tileNum = 0
		var/mapStep = from_png ? "\[3/5]" : "\[2/4]"
		var/writeStep = from_png ? "\[4/5]" : "\[3/4]"
		var/doneStep = from_png ? "\[5/5]" : "\[4/4]"

		src << "[mapStep] Mapping tiles (0/[totalTiles], tileset size [tilesetCount])..."

		for(var/i in iconStates)
			tileNum++
			var/newI
			if(!d)
				newI = findDuplicate(i,map,tileset)
			if(newI)
				reused++
			else
				newI = tilesetCount + 1
				var/icon/is = new(map, icon_state = i)
				tileset.Insert(is,icon_state = "[newI]")
				tilesetCount++
				indexTilesetState("[newI]")
				added++

			var/existingKey = keyByTileId["[newI]"]
			if(existingKey)
				tilePosList += existingKey
			else
				var/l1 = alphabet[curX]
				var/l2 = alphabet[curY]
				var/key = "[l1][l2]"
				keyByTileId["[newI]"] = key
				tilePosList += key
				curY ++
				if(curY == alphabet.len+1)
					curY = 1
					curX ++

				map_text += "\"[key]\"=(/turf/{name=\"[newI]\"; icon = 'INSERT_DMI_HERE'; icon_state = \"[newI]\"},/area)\n"

			if(!(tileNum % 50) || tileNum == totalTiles)
				src << "  ... tile [tileNum]/[totalTiles] (reused [reused], new [added], tileset [tilesetCount])"

		map_text += "\n(1,1,1) = {\"\n"


		var/counter
		var/mapPos
		var/list/row = list()
		for(var/i=tilePosList.len, i > 0, i--)
			counter++
			if(counter > maxX)
				counter = 1

				for(var/x=row.len, x > 0, x--)
					var/y = row[x]
					mapPos += "[y]"
				mapPos += "\n"
				row = list()
			var/x = tilePosList[i]
			row += "[x]"

		for(var/x=row.len, x > 0, x--)
			var/y = row[x]
			mapPos += "[y]"

		map_text += "[mapPos]\n\"}"
		var/outPath = "Maps/[folder][copytext(fileName,1,length(fileName)-3)].dmm"
		var/outSlash = findlasttext(outPath, "/")
		if(outSlash)
			ensureFolder(copytext(outPath, 1, outSlash))
		src << "[writeStep] Writing [outPath]"
		text2file(map_text,outPath)

		src << "[doneStep] Done: [fileName] (reused [reused], new [added], tileset [tilesetCount])"
