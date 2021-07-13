#!/usr/bin/env ipython
#!/usr/bin/env python
# coding: utf-8

#from pathlib import Path

#FONT = str(Path('./fonts/Open_Sans/OpenSans-Regular.ttf').resolve())

layout_defaults = {'image': None, 
                   'max_lines': 1, 
                   'padding': 0, 
                   'width': 1, 
                   'height': 1, 
                   'abs_coordinates': (None, None), 
                   'hcenter': False, 
                   'vcenter': False, 
                   'rand': False, 
                   'align': 'left',
                   'inverse': False, 
                   'relative': False, 
                   'font': None, 
                   'font_size': None, 
                   'maxchar': None, 
                   'dimensions': None,
                   'padding': 0,
                   'mode': '1',
                   'fill': 0,
                   'bkground': 255}


# US English - Upper and lower case letters
USA_CHARDIST = {
'A': 0.0796394951934866,
'B': 0.0480421724743304,
'C': 0.0650193941562118,
'D': 0.0367478368492653,
'E': 0.0392455626459735,
'F': 0.0285607049987683,
'G': 0.0264235633824497,
'H': 0.0350469680738427,
'I': 0.063304067996198,
'J': 0.0223114296397362,
'K': 0.0132044112598647,
'L': 0.0303276241783032,
'M': 0.0735552041056704,
'N': 0.058228959048466,
'O': 0.0299636382603628,
'P': 0.0408886018830318,
'Q': 0.00330507150877549,
'R': 0.0415148050705166,
'S': 0.0864526085515713,
'T': 0.092261358897769,
'U': 0.0162965906935831,
'V': 0.00880284634720004,
'W': 0.0303874380635722,
'X': 0.00214819726335884,
'Y': 0.026731137152672,
'Z': 0.0015903123050202,
'a': 0.0853444241209682,
'b': 0.014043443886782,
'c': 0.0317851933335035,
'd': 0.0384231410874873,
'e': 0.125522566035832,
'f': 0.0210277287958113,
'g': 0.019565625337748,
'h': 0.0479248841551587,
'i': 0.0734040206369666,
'j': 0.00106775804890564,
'k': 0.00747099878278566,
'l': 0.0413955994606343,
'm': 0.0237913407247777,
'n': 0.0735371823360625,
'o': 0.0766780830435463,
'p': 0.0203573642991815,
'q': 0.000879113659646998,
'r': 0.0670907487656561,
's': 0.0678732298030442,
't': 0.0892991141869109,
'u': 0.0261576563826317,
'v': 0.0105934322827605,
'w': 0.0164673662068651,
'x': 0.00200361905383887,
'y': 0.0172194144536526,
'z': 0.00107695111884201,
}

# French
FRA_CHARDIST = {
'a': 0.07636,
'b': 0.00901,
'c': 0.0326,
'd': 0.03669,
'e': 0.14715,
'f': 0.01066,
'g': 0.00866,
'h': 0.00737,
'i': 0.07529,
'j': 0.00613,
'k': 0.00074,
'l': 0.05456,
'm': 0.02968,
'n': 0.07095,
'o': 0.05796,
'p': 0.02521,
'q': 0.01362,
'r': 0.06693,
's': 0.07948,
't': 0.07244,
'u': 0.06311,
'v': 0.01838,
'w': 0.00049,
'x': 0.00427,
'y': 0.00128,
'z': 0.00326,
'à': 0.00486,
'â': 0.00051,
'á': 0,
'å': 0,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0.00018,
'ç': 0.00085,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0.00271,
'é': 0.01504,
'ê': 0.00218,
'ë': 0.00008,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0.00045,
'ì': 0,
'í': 0,
'ï': 0.00005,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0,
'ô': 0.00023,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0.00058,
'ú': 0,
'û': 0.0006,
'ŭ': 0,
'ü': 0,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,    
}

# German
DEU_CHARDIST = {
'a': 0.06516,
'b': 0.01886,
'c': 0.02732,
'd': 0.05076,
'e': 0.16396,
'f': 0.01656,
'g': 0.03009,
'h': 0.04577,
'i': 0.0655,
'j': 0.00268,
'k': 0.01417,
'l': 0.03437,
'm': 0.02534,
'n': 0.09776,
'o': 0.02594,
'p': 0.0067,
'q': 0.00018,
'r': 0.07003,
's': 0.0727,
't': 0.06154,
'u': 0.04166,
'v': 0.00846,
'w': 0.01921,
'x': 0.00034,
'y': 0.00039,
'z': 0.01134,
'à': 0,
'â': 0,
'á': 0,
'å': 0,
'ä': 0.00578,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0.00443,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0.00307,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0,
'û': 0,
'ŭ': 0,
'ü': 0.00995,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,    
}

# Spanish
ESP_CHARDIST = {
'a': 0.11525,
'b': 0.02215,
'c': 0.04019,
'd': 0.0501,
'e': 0.12181,
'f': 0.00692,
'g': 0.01768,
'h': 0.00703,
'i': 0.06247,
'j': 0.00493,
'k': 0.00011,
'l': 0.04967,
'm': 0.03157,
'n': 0.06712,
'o': 0.08683,
'p': 0.0251,
'q': 0.00877,
'r': 0.06871,
's': 0.07977,
't': 0.04632,
'u': 0.02927,
'v': 0.01138,
'w': 0.00017,
'x': 0.00215,
'y': 0.01008,
'z': 0.00467,
'à': 0,
'â': 0,
'á': 0.00502,
'å': 0,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0.00433,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0.00725,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0.00311,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0,
'ô': 0,
'ó': 0.00827,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0.00168,
'û': 0,
'ŭ': 0,
'ü': 0.00012,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Portugese 
PRT_CHARDIST = {
'a': 0.14634,
'b': 0.01043,
'c': 0.03882,
'd': 0.04992,
'e': 0.1257,
'f': 0.01023,
'g': 0.01303,
'h': 0.00781,
'i': 0.06186,
'j': 0.00397,
'k': 0.00015,
'l': 0.02779,
'm': 0.04738,
'n': 0.04446,
'o': 0.09735,
'p': 0.02523,
'q': 0.01204,
'r': 0.0653,
's': 0.06805,
't': 0.04336,
'u': 0.03639,
'v': 0.01575,
'w': 0.00037,
'x': 0.00253,
'y': 0.00006,
'z': 0.0047,
'à': 0.00072,
'â': 0.00562,
'á': 0.00118,
'å': 0,
'ä': 0,
'ã': 0.00733,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0.0053,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0.00337,
'ê': 0.0045,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0.00132,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0,
'ô': 0.00635,
'ó': 0.00296,
'õ': 0.0004,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0.00207,
'û': 0,
'ŭ': 0,
'ü': 0.00026,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Italian
ITA_CHARDIST = {
'a': 0.11745,
'b': 0.00927,
'c': 0.04501,
'd': 0.03736,
'e': 0.11792,
'f': 0.01153,
'g': 0.01644,
'h': 0.00636,
'i': 0.10143,
'j': 0.00011,
'k': 0.00009,
'l': 0.0651,
'm': 0.02512,
'n': 0.06883,
'o': 0.09832,
'p': 0.03056,
'q': 0.00505,
'r': 0.06367,
's': 0.04981,
't': 0.05623,
'u': 0.03011,
'v': 0.02097,
'w': 0.00033,
'x': 0.00003,
'y': 0.0002,
'z': 0.01181,
'à': 0.00635,
'â': 0, 
'á': 0,
'å': 0,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0.00263,
'é': 0,
'ê': 0, 
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0.0003,
'í': 0.0003,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0.00002,
'ö': 0,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0.00166,
'ú': 0.00166,
'û': 0,
'ŭ': 0,
'ü': 0,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Turkish
TUR_CHARDIST = {
'a': 0.1192,
'b': 0.02844,
'c': 0.00963,
'd': 0.04706,
'e': 0.08912,
'f': 0.00461,
'g': 0.01253,
'h': 0.01212,
'i': 0,
'j': 0.00034,
'k': 0.04683,
'l': 0.05922,
'm': 0.03752,
'n': 0.07487,
'o': 0.02476,
'p': 0.00886,
'q': 0,
'r': 0.06722,
's': 0.03014,
't': 0.03314,
'u': 0.03235,
'v': 0.00959,
'w': 0,
'x': 0,
'y': 0.03336,
'z': 0.015,
'à': 0,
'â': 0,
'á': 0,
'å': 0,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0.01156,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0.01125,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0.00777,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0.0178,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0,
'û': 0,
'ŭ': 0,
'ü': 0.01854,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Swedish
SWE_CHARDIST = {
'a': 0.09383,
'b': 0.01535,
'c': 0.01486,
'd': 0.04702,
'e': 0.10149,
'f': 0.02027,
'g': 0.02862,
'h': 0.0209,
'i': 0.05817,
'j': 0.00614,
'k': 0.0314,
'l': 0.05275,
'm': 0.03471,
'n': 0.08542,
'o': 0.04482,
'p': 0.01839,
'q': 0.0002,
'r': 0.08431,
's': 0.0659,
't': 0.07691,
'u': 0.01919,
'v': 0.02415,
'w': 0.00142,
'x': 0.00159,
'y': 0.00708,
'z': 0.0007,
'à': 0,
'â': 0,
'á': 0,
'å': 0.01338,
'ä': 0.01797,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0.01305,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0,
'û': 0,
'ŭ': 0,
'ü': 0,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Dutch
NED_CHARDIST = {
'a': 0.07486,
'b': 0.01584,
'c': 0.01242,
'd': 0.05933,
'e': 0.1891,
'f': 0.00805,
'g': 0.03403,
'h': 0.0238,
'i': 0.06499,
'j': 0.0146,
'k': 0.02248,
'l': 0.03568,
'm': 0.02213,
'n': 0.10032,
'o': 0.06063,
'p': 0.0157,
'q': 0.00009,
'r': 0.06411,
's': 0.0373,
't': 0.0679,
'u': 0.0199,
'v': 0.0285,
'w': 0.0152,
'x': 0.00036,
'y': 0.00035,
'z': 0.0139,
'à': 0,
'â': 0,
'á': 0,
'å': 0,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0,
'û': 0,
'ŭ': 0,
'ü': 0,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}

# Danish
DAN_CHARDIST = {
'a': 0.06025,
'b': 0.02,
'c': 0.00565,
'd': 0.05858,
'e': 0.15453,
'f': 0.02406,
'g': 0.04077,
'h': 0.01621,
'i': 0.06,
'j': 0.0073,
'k': 0.03395,
'l': 0.05229,
'm': 0.03237,
'n': 0.0724,
'o': 0.04636,
'p': 0.01756,
'q': 0.00007,
'r': 0.08956,
's': 0.05805,
't': 0.06862,
'u': 0.01979,
'v': 0.02332,
'w': 0.00069,
'x': 0.00028,
'y': 0.00698,
'z': 0.00034,
'à': 0,
'â': 0,
'á': 0,
'å': 0.0119,
'ä': 0,
'ã': 0,
'ą': 0,
'æ': 0.00872,
'œ': 0,
'ç': 0,
'ĉ': 0,
'ć': 0,
'č': 0,
'ď': 0,
'ð': 0,
'è': 0,
'é': 0,
'ê': 0,
'ë': 0,
'ę': 0,
'ě': 0,
'ĝ': 0,
'ğ': 0,
'ĥ': 0,
'î': 0,
'ì': 0,
'í': 0,
'ï': 0,
'ı': 0,
'ĵ': 0,
'ł': 0,
'ñ': 0,
'ń': 0,
'ň': 0,
'ò': 0,
'ö': 0,
'ô': 0,
'ó': 0,
'õ': 0,
'ø': 0.00939,
'ř': 0,
'ŝ': 0,
'ş': 0,
'ś': 0,
'š': 0,
'ß': 0,
'ť': 0,
'þ': 0,
'ù': 0,
'ú': 0,
'û': 0,
'ŭ': 0,
'ü': 0,
'ů': 0,
'ý': 0,
'ź': 0,
'ż': 0,
'ž': 0,
}


