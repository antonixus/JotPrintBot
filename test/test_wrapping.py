from escpos.printer import Serial

p = Serial(devfile='/dev/serial0', baudrate=9600)

# Тест Font A
p.font('a')
p.text("12345678901234567890123456789012   <-- 32 chars\n")
p.text("Should be 32 chars max in Font A\n")
p.cut()

# Тест Font B
p.font('b')
p.text("123456789012345678901234567890123456789012   <-- try 42\n")
p.text("Should fit ~42 chars in Font B\n")
p.cut()