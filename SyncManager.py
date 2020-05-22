import math

class SyncManager:
	def create_fractions (self, n):
		fractions = [(k/i, k, i) for i in range(1,n+1) for k in range (1,i)]
		delete = []
		for f in fractions:
			for k in fractions:
				if f != k and f[0] == k[0]:
					if f[2] < k[2]:
						delete.append (k)
					else:
						delete.append (f)
						
		fractions = [f for f in fractions if f not in delete]
		
		fractions.sort(key=lambda x: x[0])
		return [(0, 0, 1)] + fractions + [(1, 1, 1)]
				
		
	def quantize (self, master_length, curr_length, fractions):
		q = curr_length / master_length
		qq = q % 1
		
		for i in range(len(fractions)):
			if qq < fractions[i][0]:
				
				if abs(qq - fractions[i-1][0]) < abs(fractions[i][0] - qq):
					return (math.floor(q) + fractions[i-1][0], fractions[i][2])
				else:
					return (math.floor(q) + fractions[i][0], fractions[i][2])
	
	def __init__(self):
		self.q_fractions = self.create_fractions (4)
	
	def calc_sync_samples (self, master, current):
		q = self.quantize ( len(master.samples), len(current.samples), self.q_fractions )
		length = q[0]
		if length > 0 and length != 1:
			for k in range(q[1] - 1):
				new_sync_sample = ( current.sync_samples[-1] + len(master.samples) * length ) % len(master.samples)
				current.sync_samples.append (new_sync_sample)
				
			current.sync_samples = [round(i) for i in current.sync_samples]
	
