local ffiutil = require("ffi/util")
local util = require("util")

local pid_path = "/tmp/dropbear_koreader.pid"
local handle = io.open(pid_path, "r")
if not handle then
    return
end

local pid = tonumber(handle:read("*l"))
handle:close()
if not pid then
    os.remove(pid_path)
    return
end

os.execute(string.format("pkill -TERM -P %d 2>/dev/null; kill -TERM %d 2>/dev/null", pid, pid))
for _ = 1, 20 do
    if not util.pathExists("/proc/" .. pid) then
        break
    end
    ffiutil.sleep(0.1)
end

if util.pathExists("/proc/" .. pid) then
    os.execute(string.format("pkill -KILL -P %d 2>/dev/null; kill -KILL %d 2>/dev/null", pid, pid))
end
os.remove(pid_path)
