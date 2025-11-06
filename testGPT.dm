client/proc
    dmi_to_map(icon/map, folder, fileName, d = 0)
        var/list/iconStates = map.IconStates()
        var/lastState = iconStates[iconStates.len]
        var/maxX = text2num(splittext(lastState, ",")[1]) + 1

        var/map_text = ""
        var/curX = 1
        var/curY = 1
        var/list/tilePosList = list()

        for (var/i in map.IconStates())
            //world << i
            var/newI
            if (!d)
                newI = findDuplicate(i, map, tileset)
            if (!newI)
                newI = text2num(length(tileset.IconStates())) + 1
                var/icon/is = new(map, icon_state = i)
                tileset.Insert(is, icon_state = "[newI]")

            var/l1 = alphabet[curX]
            var/l2 = alphabet[curY]

            var/objExists = findtext(map_text, "\"=[newI]\"=")
            if (objExists)
                tilePosList += copytext(map_text, objExists - 2, objExists)
            else
                tilePosList += "[l1][l2]"
                curY++
                if (curY == alphabet.len + 1)
                    curY = 1
                    curX++

                map_text += "\"[l1][l2]\"=[newI]\"="
            // "ab"=(/turf/tile/{icon_state = "is"},/area)="

        map_text += "}=\n(1,1,1)={\n"

        var/counter = 0
        var/mapPos = ""
        var/list/row = list()

        for (var/i = tilePosList.len, i > 0, i--)
            counter++
            if (counter > maxX)
                counter = 1

                for (var/x = row.len, x > 0, x--)
                    var/y = row[x]
                    mapPos += "[y]"
                mapPos += "\n"
                row = list()

            var/x = tilePosList[i]
            row += "[x]"

        for (var/x = row.len, x > 0, x--)
            var/y = row[x]
            mapPos += "[y]"

        map_text += "[mapPos]\"}"

        text2file(map_text, "Maps/[folder][copytext(fileName, 1, length(fileName) - 3)].dmm")

        src << "Finished Converting: [fileName]"
