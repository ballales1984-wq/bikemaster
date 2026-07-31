const fs = require('fs');
const origSymlinkSync = fs.symlinkSync;
fs.symlinkSync = function (src, dst, type) {
  console.log('[PATCH] Copying instead of symlinking: ' + src + ' -> ' + dst);
  try {
    fs.copyFileSync(src, dst);
  } catch (e) {
    console.error('[PATCH] Copy failed:', e.message);
  }
};
console.log('fs.symlinkSync patched to use copyFile');
