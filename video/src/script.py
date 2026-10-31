"""Narration, one entry per scene (wording supplied by the project brief; numbers from results/*.json)."""
SCENES = [
    ("s1", "October fifth, 2024. Playoff baseball in Cleveland. Ninth inning, seven to nothing. "
           "Emmanuel Clase's first pitch to Matt Vierling bounces in the dirt. Nobody blinks."),
    ("s2", "Two years later, federal prosecutors list it among eighteen pitches they say were sold to bettors. "
           "Bettors allegedly won at least four hundred thousand dollars. Both pitchers have pleaded not guilty."),
    ("s3", "Every alarm so far came from the betting side: someone noticed strange money. We asked a different "
           "question. Can the pitch-tracking data itself reveal a fix? And how many innocent pitchers would that alarm catch?"),
    ("s4", "We pulled every MLB pitch from 2023 to 2025. Two point one eight million pitches. "
           "And matched all eighteen court-named pitches, one to one."),
    ("s5", "First, single pitches. We locked our model in git before testing it. It lost to a one-line rule: "
           "average precision 0.10 against 0.20. A rigged ball in the dirt looks like an ordinary miss, "
           "and six of the eighteen were not even balls."),
    ("s6", "So we watched patterns instead: each pitcher's own rate of first pitches thrown into the dirt. "
           "In May 2025, Clase did it nine times in forty-one at-bats. Three and a half times his normal."),
    ("s7", "Against every pitcher-month in baseball, that month ranks twenty-second of eight thousand three hundred "
           "thirty-nine, ahead of simple rules that rank it thirty-first and seven hundred eighty-third. "
           "That is about one alert a month for the whole league. A live monitor would have flagged it on June first, "
           "a month before he was placed on leave."),
    ("s8", "It is not magic. It caught one of seven named months. The 2023 pitches and Ortiz's two were too sparse "
           "to move a monthly rate."),
    ("s9", "It never says rigged. It tells a human where to look. Pitch Integrity Monitor. Real data, honest limits."),
]
