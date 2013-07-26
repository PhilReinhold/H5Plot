from data_server import DataServerClient
import time

c = DataServerClient()

c['test.h5']['a'] = [1,2,3,4,3,2,1]

time.sleep(2)

print 'Done'