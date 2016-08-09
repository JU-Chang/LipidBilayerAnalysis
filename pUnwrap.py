#numpy
import numpy as np
#MDAnalysis
import MDAnalysis as mda
#multiprocessing module
import multiprocessing as mp

def mda_wrap_coordinates(abc, coord, refcoord):
	wrapcoord = coord.copy()
	# box vectors (assuming rectangular)
	A = abc[0]
	B = abc[1]
	C = abc[2]
	Ah = A/2.0
	Bh = B/2.0
	Ch = C/2.0
	iA = 1.0/A
	iB = 1.0/B
	iC = 1.0/C
	
	natoms = len(coord)
	#list to hold shifts
	sAs = np.zeros(natoms)
	sBs = np.zeros(natoms)
	sCs = np.zeros(natoms)

	#compute the difference in the z coordinate
	dzs = coord[:,2] - refcoord[:,2]
	#compute the required shift
	i = 0
	for dz in dzs:
		shift = 0
		if	dz > Ch:
			shift-=1
			while (dz+shift*C)>Ch:
				shift-=1
		elif dz < -Ch:
			shift+=1
			while (dz+shift*C)<-Ch:
				shift+=1
		sCs[i]=shift
		i+=1
	#apply shift
	wrapcoord[:,2] += (sCs*C)
	#compute the difference in the y coordinate
	dys = coord[:,1] - refcoord[:,1]
	#compute the required shift
	i = 0
	for dy in dys:
		shift = 0
		if	dy > Bh:
			shift-=1
			while (dy+shift*B)>Bh:
				shift-=1
		elif dy < -Bh:
			shift+=1
			while (dy+shift*B)<-Bh:
				shift+=1
		sBs[i]=shift
		i+=1
	#apply shift
	wrapcoord[:,1] += (sBs*B)
	#compute the difference in the x coordinate
	dxs = coord[:,0] - refcoord[:,0]
	#compute the required shift
	i = 0
	for dx in dxs:
		shift = 0
		if	dx > Ah:
			shift-=1
			while (dx+shift*A)>Ah:
				shift-=1
		elif dx < -Ah:
			shift+=1
			while (dz+shift*A)<-Ah:
				shift+=1
		sAs[i]=shift
		i+=1
	#apply shift
	wrapcoord[:,0] += (sAs*A)
	return wrapcoord


def mda_wrap_coordinates_parallel(abc, coord, refcoord,nprocs=2):
	
	index_ranges = []
	total_atoms = len(coord)
	atoms_per_proc_base = total_atoms/nprocs
	left_over = total_atoms % (atoms_per_proc_base * nprocs)
	#print "total atoms ",total_atoms
	#print "atoms per proc ",atoms_per_proc_base
	#print "left over ",left_over
	#assign base ranges
	for i in xrange(nprocs):
		fs = i*atoms_per_proc_base
		fe = fs + atoms_per_proc_base - 1
		index_ranges.append([fs,fe])
	#print "index_ranges (pre-adjust):"	
	#print index_ranges
	#now adjust for leftovers - divide them "equally" over the processes
	lo = left_over
	while lo > 0:
		for i in xrange(nprocs):
			index_ranges[i][1]+=1
			for j in xrange(i+1,nprocs):
				index_ranges[j][0]+=1
				index_ranges[j][1]+=1
			lo-=1
			if lo == 0:
				break
	
	#print "nprocs ",nprocs
	#print "index_ranges (post adjust): "
	#print index_ranges
	#now build the sub coordinate list
	#coords
	c = []
	#reference
	r = []	
	for i in xrange(nprocs):
		sfs = index_ranges[i][0]
		sfe = index_ranges[i][1]+1
		c.append(coord[sfs:sfe])
		r.append(refcoord[sfs:sfe])

	wrap_func = mda_wrap_coordinates 
	#create process pool
	pool = mp.Pool(processes=nprocs)
	results = [pool.apply_async(wrap_func,args=(abc,c[i],r[i])) for i in range(0,nprocs)]
#	print "results:"
#	print results
	results_ordered = [p.get() for p in results]
#	print "results ordered: "
#	print results_ordered
#		#collect results  into single array for return
	i = 0
	wrapcoord = np.zeros((total_atoms,3))
#	print "len(results_ordered) ",len(results_ordered)
	for p in results_ordered:
		fs = index_ranges[i][0]
		fe = index_ranges[i][1]
		#print fs, fe
		#print msd[fs:(fe+1)].shape
		#print p[:].shape
		wrapcoord[fs:(fe+1)] = p[:]
		i+=1
	pool.close()
	pool.join()
	
	return wrapcoord



def mda_unwrap(universe, out_file_name):
	frames = universe.trajectory
	print "unwrapping coordinates - ouput is ",out_file_name
	nframes=len(frames)
	# Setup writer to write aligned dcd file
	writer = mda.coordinates.DCD.DCDWriter(
		out_file_name, frames.n_atoms,
		0,
		1,
		frames.dt,
		remarks='Unwrapped trajectory')
	natoms = frames.n_atoms
	oldcoord = np.zeros((natoms,3), dtype=np.double)
	firstframe = True
	for frame in frames:
		currcoord = frame._pos[:]
		if firstframe:
			oldcoord = currcoord
			firstframe = False
			writer.write(universe.atoms)
		else:
			abc = frame.dimensions[0:3]
			wrapcoord = mda_wrap_coordinates(abc, currcoord, oldcoord)
			frame._pos[:] = wrapcoord[:]
			writer.write(universe.atoms)


def mda_unwrap_parallel(universe, out_file_name,nprocs=2):
	frames = universe.trajectory
	print "unwrapping coordinates - ouput is ",out_file_name
	nframes=len(frames)
	# Setup writer to write aligned dcd file
	writer = mda.coordinates.DCD.DCDWriter(
		out_file_name, frames.n_atoms,
		0,
		1,
		frames.dt,
		remarks='Unwrapped trajectory')
	natoms = frames.n_atoms
	oldcoord = np.zeros((natoms,3), dtype=np.double)
	firstframe = True
	for frame in frames:
		currcoord = frame._pos[:]
		if firstframe:
			oldcoord = currcoord
			firstframe = False
			writer.write(universe.atoms)
		else:
			abc = frame.dimensions[0:3]
			wrapcoord = mda_wrap_coordinates_parallel(abc, currcoord, oldcoord,nprocs=2)
			frame._pos[:] = wrapcoord[:]
			writer.write(universe.atoms)


#def wrap_coordinates(abc, coord, refcoord):
#	wrapcoord = coord.copy()
#	# box vectors (assuming rectangular)
#	A = abc[0]
#	B = abc[1]
#	C = abc[2]
#	Ah = A/2.0
#	Bh = B/2.0
#	Ch = C/2.0
#	iA = 1.0/A
#	iB = 1.0/B
#	iC = 1.0/C
#	
#	natoms = 1
#	#list to hold shifts
#	sAs = np.zeros(natoms)
#	sBs = np.zeros(natoms)
#	sCs = np.zeros(natoms)

#	#compute the difference in the z coordinate
#	dz = coord[2] - refcoord[2]
#	#compute the required shift
#	i = 0
#	shift = 0
#	if	dz > Ch:
#		shift-=1
#		while (dz+shift*C)>Ch:
#			shift-=1
#	elif dz < -Ch:
#		shift+=1
#		while (dz+shift*C)<-Ch:
#			shift+=1
#	sCs[i]=shift
#	#apply shift
#	wrapcoord[2] += (sCs*C)
#	#compute the difference in the y coordinate
#	dy = coord[1] - refcoord[1]
#	#compute the required shift
#	i = 0

#	shift = 0
#	if	dy > Bh:
#		shift-=1
#		while (dy+shift*B)>Bh:
#			shift-=1
#	elif dy < -Bh:
#		shift+=1
#		while (dy+shift*B)<-Bh:
#			shift+=1
#	sBs[i]=shift
#	i+=1
#	#apply shift
#	wrapcoord[1] += (sBs*B)
#	#compute the difference in the x coordinate
#	dx = coord[0] - refcoord[0]
#	#compute the required shift
#	i = 0
#	shift = 0
#	if	dx > Ah:
#		shift-=1
#		while (dx+shift*A)>Ah:
#			shift-=1
#	elif dx < -Ah:
#		shift+=1
#		while (dz+shift*A)<-Ah:
#			shift+=1
#	sAs[i]=shift
#	
#	#apply shift
#	wrapcoord[0] += (sAs*A)
#	return wrapcoord			
