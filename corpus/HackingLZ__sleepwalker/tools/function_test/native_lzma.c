#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "sw_core.h"
#include "sw_impl.h"

/* xz --format=raw --lzma1=preset=9e,lc=3,lp=0,pb=2,dict=1MiB of 0c0001 */
static const uint8_t raw[] = {
    0x00,0x05,0xff,0xfc,0x48, 0x88,0x1f,0xff,0xff,0xf4,0x86,0x80,0x00
};

int main(void) {
    uint8_t out[64];
    /* Try candidate props. The first 5 bytes are one candidate; also try the
     * standard 7z props for lc=3,lp=0,pb=2, dict 1MiB: 5d 00 00 10 00. */
    const uint8_t *cands[] = {
        (const uint8_t[]){0x5d,0x00,0x00,0x10,0x00},
        (const uint8_t[]){0x00,0x05,0xff,0xfc,0x48},
        (const uint8_t[]){0x5d,0x00,0x00,0x01,0x00},
        (const uint8_t[]){0x5d,0x00,0x00,0x00,0x01},
    };
    for (int i=0;i<4;i++){
        memset(out,0,sizeof out);
        /* try full raw as stream */
        int rc = sw_lzma_decompress(cands[i], raw+5, sizeof(raw)-5, out, 3);
        printf("cand %d props=%02x%02x%02x%02x%02x stream=raw+5 rc=%d out=%02x%02x%02x\n",
               i,cands[i][0],cands[i][1],cands[i][2],cands[i][3],cands[i][4],rc,out[0],out[1],out[2]);
        /* try whole raw as stream, props passed separately */
        memset(out,0,sizeof out);
        rc = sw_lzma_decompress(cands[i], raw, sizeof(raw), out, 3);
        printf("   cand %d whole raw as stream rc=%d out=%02x%02x%02x\n", i, rc, out[0],out[1],out[2]);
    }
    return 0;
}
