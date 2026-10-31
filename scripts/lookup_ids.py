import pybaseball as pb
pb.cache.enable()
for last, first in [("clase", "emmanuel"), ("ortiz", "luis")]:
    print(pb.playerid_lookup(last, first, fuzzy=False).to_string())
