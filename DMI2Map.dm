// honestly i've no clue if changing the fps would decrease the render time for each map

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
		fps = 1000
		return ..()
client
	fps = 100

var/list
	alphabet = list()
// tileset is 8x92

proc/compareIcon(icon/a,icon/b,state1,state2) // Assumes that both icons are same dimensions
    var/h = a.Height()
    var/w = a.Width()
    var/counter=0

    for(var/i = 1, i <= w, i++)
        for(var/j = 1, j <= h, j++)
            if(a.GetPixel(i,j,state1) != b.GetPixel(i,j,state2)) return 0
            counter++
            if(counter % 100 == 0) // Only update every 100 iterations
                STATUS_COMPARE_ICON = "In Process ([counter]/[h*w])"

    return 1

proc/findDuplicate(state,icon/a,icon/b) // if true, it returns an icon_state from b (is a found in b)
	var/list/icon_states = b.IconStates()
	var/n = icon_states.len
	var/counter = 0
	for(var/x in icon_states)
		counter++
		if(counter % 10 == 0) // Update status less often
			STATUS_FIND_DUPLICATE = "In Process ([counter] / [n] searched)"
		if(compareIcon(a,b,state,x))
			return x // returns the icon_state name
	STATUS_FIND_DUPLICATE = "Done for [state]."
	return 0


proc/isFolder(var/t)
	return copytext(t,length(t)) == "/"

proc/isDMI(var/t)
	return findtext(t,".dmi")

var/tilesetName
var/icon/tileset

proc/saveTileset()
	fcopy(tileset,"Tilesets/[tilesetName]")
	world << "Tileset [tilesetName] saved."

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
		else
			tileset = new(file("Tilesets/[t]"))
			tilesetName = t

		src << "Set tileset to [tilesetName]"



client/verb
	ConvertDMI()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/dmiFolder = flist("DMI/")

		if(dmiFolder.len)
			var/dmi = input("Select to convert.") as null | anything in dmiFolder
			if(dmi)
				recursiveConvert("DMI/[dmi]")

		world << "Finished Converting Icons."
		saveTileset()

client/verb
	ConvertDMI_Duplicates()
		if(!tileset)
			world << "Error: You must set a tileset before continuing."
			return
		var/list/dmiFolder = flist("DMI/")

		if(dmiFolder.len)
			var/dmi = input("Select to convert.") as null | anything in dmiFolder
			if(dmi)
				recursiveConvert("DMI/[dmi]",1)

		world << "Finished Converting Icons."
		saveTileset()

client/proc
	recursiveConvert(t,d=0) // t can also be considered a destination

		if(isDMI(t))
			var/point = findlasttext(t,"/")+1
			var/dmiFile = copytext(t,point)
			var/dmiFolder = copytext(t,1,point)

			if(fexists("Maps/[dmiFolder][copytext(dmiFile,1,length(dmiFile)-3)].dmm"))
				world << "[dmiFile] already exists, skipping"
				return

			var/icon/map = new(file("[dmiFolder][dmiFile]"))
			dmi_to_map(FixDMI(map),dmiFolder,dmiFile,d)
			sleep(world.tick_lag)
			return

		if(isFolder(t))
			for(var/f in flist(t))
				recursiveConvert("[t][f]",d)
			return

client/proc
	dmi_to_map(icon/map, folder, fileName, d = 0)
		var/list/iconStates = map.IconStates()
		if(!iconStates || !iconStates.len)
			src << "No icon states found."
			return

		var/lastState = iconStates[iconStates.len]
		var/maxX = text2num(splittext(lastState, ",")[1]) + 1

		var/map_text = ""
		var/curX = 1
		var/curY = 1
		var/list/tilePosList = list()
		var/counterProcess = 0

		// Cache tileset icon states to avoid repeated calls
		var/list/tilesetStates = tileset.IconStates()
		if(!tilesetStates) tilesetStates = list()

		for(var/state_name in iconStates)
			STATUS_DMI2_MAP_PROCESS_1 = "[++counterProcess]/[iconStates.len]"

			var/newI
			if(!d)
				newI = findDuplicate(state_name, map, tileset)

			if(!newI)
				newI = text2num(tilesetStates.len) + 1
				var/icon/is = new(map, icon_state = state_name)
				tileset.Insert(is, icon_state = "[newI]")
				tilesetStates += "[newI]"

			var/l1 = alphabet[curX]
			var/l2 = alphabet[curY]

			// If we've already emitted this turf line, reuse its coordinate label; else create a new label + line
			var/objExists = findtext(map_text, "\"=(/turf/{name=\"[newI]\"")
			if(objExists)
				tilePosList += copytext(map_text, objExists - 2, objExists)
			else
				tilePosList += "[l1][l2]"
				curY++
				if(curY == alphabet.len + 1)
					curY = 1
					curX++

				map_text += "\"[l1][l2]\"=(/turf/{name=\"[newI]\"; icon = 'INSERT_DMI_HERE'; icon_state = \"[newI]\"},/area)\n"

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
		text2file(map_text,"Maps/[folder][copytext(fileName,1,length(fileName)-3)].dmm")

		src << "Finished Converting: [fileName]"
		ResetStatus()
