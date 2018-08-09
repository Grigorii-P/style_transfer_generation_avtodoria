from time import time

c = 0
t0 = time()
for i in range(100000000):
    c += 1
t = time() - t0
print('Average time per sample - {:.2f} sec'.format(t))