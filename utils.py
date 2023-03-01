def dist_ring (p1, p2, size):
	return min ( abs (p1 - p2), ( size - max (p1, p2) ) + min(p1, p2) )
