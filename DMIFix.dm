//Chances are this part of the code is completely unneccessary, but at the time this is the only way I could figure out how to solve the backwards map problem.

client/proc
	sort_dmi_map(fw,filename)
		var/icon/finalicon = new()
		var/icon/z = new(fw)
		var/list/states = z.IconStates()
		var/lastState = states[states.len]
		var/icon/a

		var/mx = text2num(splittext(lastState,",")[1])
		var/my = text2num(splittext(lastState,",")[2])
		var
			total=mx*my
			status
			counter=0
		for(var/i = 0, i<= my, i++)
			for(var/j=0, j<=mx, j++)
				a = new(z,"[j],[i]")
				finalicon.Insert(a,"[j],[i]")
				status = "[++counter]/[total]"
				STATUS_SORT_DMI_MAP = status
		STATUS_SORT_DMI_MAP = "FINISHED"
		fcopy(finalicon,filename)


client/proc
	FixDMI(icon/dmi) // Takes in a full map icon file and converts it to a new DMI file that DMI2Map can read and place icons properly.

		// Creating a temporary icon that has the icon_states as names to place the icon in.
		var
			icon/splitIcon = new()
			width = dmi.Width() / 32
			height = dmi.Height() / 32

		var
			total=width*height
			counter=0

		for(var/i=0,i<width,i++)
			for(var/j=0,j<height,j++)
				var
					icon/splice = new(dmi)
					x1 = (i*32) + 1
					y1 = (j*32) + 1
					x2 = ( (i+1)*32 )
					y2 = ( (j+1)*32 )

				splice.Crop(x1,y1,x2,y2)
				splitIcon.Insert(splice,"[i],[j]")

				STATUS_FIX_DMI1 = "[++counter]/[total]"
		counter=0
		STATUS_FIX_DMI1 = "FINISHED"

		// Process to sort the icon so that the map has an easier time to place the icons.
		var
			icon/finalIcon = new()
			list/states = splitIcon.IconStates()
			lastState = states[states.len]
			mx = text2num(splittext(lastState,",")[1])
			my = text2num(splittext(lastState,",")[2])

		total = mx*my

		for(var/i = 0, i<= my, i++)
			for(var/j=0, j<=mx, j++)
				var/icon/a = new(splitIcon,"[j],[i]")
				finalIcon.Insert(a,"[j],[i]")

				STATUS_FIX_DMI2="[++counter]/[total]"

		STATUS_FIX_DMI2 = "FINISHED"

		return finalIcon