import re

x = "Ia=0.00	temp=23.22	LaserON=0"

y = re.findall(r'([^=\t ]*)=([-0-9\.]+)', x)

print(y)
