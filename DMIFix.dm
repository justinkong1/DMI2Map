//Chances are this part of the code is completely unneccessary, but at the time this is the only way I could figure out how to solve the backwards map problem.

client/proc
	sort_dmi_map(var/fw,var/filename)
		var/icon/finalicon = new()
		var/icon/z = new(fw)
		var/list/states = z.IconStates()
		var/lastState = states[states.len]

		var/mx = text2num(splittext(lastState,",")[1])
		var/my = text2num(splittext(lastState,",")[2])

		for(var/i = 0, i<= my, i++)
			for(var/j=0, j<=mx, j++)
				var/icon/a = new(z,"[j],[i]")
				finalicon.Insert(a,"[j],[i]")

		fcopy(finalicon,filename)


client/proc
	FixDMI(icon/dmi) // Takes in a full map icon file and converts it to a new DMI file that DMI2Map can read and place icons properly.

		// Crop tiles in y-major / x-minor order so IconStates() matches what dmi_to_map expects.
		var
			icon/finalIcon = new()
			width = dmi.Width() / 32
			height = dmi.Height() / 32

		for(var/j = 0, j < height, j++)
			for(var/i = 0, i < width, i++)
				var
					icon/splice = new(dmi)
					x1 = (i * 32) + 1
					y1 = (j * 32) + 1
					x2 = ((i + 1) * 32)
					y2 = ((j + 1) * 32)

				splice.Crop(x1, y1, x2, y2)
				finalIcon.Insert(splice, "[i],[j]")

		return finalIcon
