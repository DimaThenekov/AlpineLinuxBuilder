#!/usr/bin/env node

import path from "node:path";
import fs from "node:fs";
import url from "node:url";
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const V86 = require('./dist/libv86.js');

const __dirname = url.fileURLToPath(new URL(".", import.meta.url));

const V86_ROOT = path.join(__dirname, "./dist/");
const OUTPUT_FILE = path.join(V86_ROOT, "alpine-state.bin");

var emulator = new V86({
    wasm_path: path.join(V86_ROOT, "v86.wasm"),
    bios: { url: path.join(V86_ROOT, "seabios.bin") },
    vga_bios: { url: path.join(V86_ROOT, "vgabios.bin") },
    autostart: true,
    memory_size: 512 * 1024 * 1024,
    vga_memory_size: 8 * 1024 * 1024,
    net_device: {
      relay_url: 'fetch',
      type: 'virtio',
      router_ip: '192.168.86.1',
      vm_ip: '192.168.86.200',
    },
    bzimage_initrd_from_filesystem: true,
    cmdline: "rw root=host9p rootfstype=9p rootflags=trans=virtio,cache=loose modules=virtio_pci tsc=reliable init_on_free=on",
    filesystem: {
        baseurl: path.join(V86_ROOT, "alpine-rootfs-flat"),
        basefs: path.join(V86_ROOT, "alpine-fs.json"),
    },
});
(function f(){
	if (emulator.fs9p) {
		const cache = new Map();
		emulator.fs9p.storage.load_from_server = async function(filePath) {
			if (cache.get(filePath)) return cache.get(filePath);
			
			const url = emulator.fs9p.storage.baseurl + filePath;
			let data = new Uint8Array(fs.readFileSync(url, null));
			
			if (url.endsWith(".zst")) {
				data = new Uint8Array(emulator.zstd_decompress(+url.match(/-(\d+)./)[1], data));
			}
			
			cache.set(filePath, data);
			return data;
		}
	} else setTimeout(f);
})();
console.log("Now booting, please stand by ...");

let serial_text = "";
let booted = false;

emulator.add_listener("serial0-output-byte", function(byte)
{
    const c = String.fromCharCode(byte);
    process.stdout.write(c);

    serial_text += c;

    if(!booted && serial_text.endsWith(":~# "))
    {
        console.log("booted");
        booted = true;

        emulator.serial0_send("sync;echo 3 >/proc/sys/vm/drop_caches\n");

        setTimeout(async function ()
            {
                const s = await emulator.save_state();

                fs.writeFile(OUTPUT_FILE, new Uint8Array(s), function(e)
                    {
                        if(e) throw e;
                        console.log("Saved as " + OUTPUT_FILE);
                        emulator.destroy();
                    });
            }, 10 * 1000);
    }
});
