package main

// Obscure / hide credentials in the source code.
// This is by no means intended to be an encryption or similar. It will simply make your
// WLAN IPs and access codes unreadable.
// Just in case your ESP gets stolen (from your external XMas light show installation)
// If connected to USB it would be very easy to identify the passwords in the source files,
// even if the files have been compiled with mpy-cross - which you should do in any case
//
// The compiled files will make it at least much harder to get the password out of the source.
// You would need some debugging and slightly deeper knowledge.
//

// go run main.go    192.168.178.2   meinpasswort-1   10.10.4.2    deinpw-2
//
// go run main.go -m -o c.py iot-ssid iot-pw   alternate-ssid alternate-pw
//
// will generate a Python file where you can call
//
// import xx
//
// xx.i(0)  -> first IP as string (192.168.178.2)
// xx.s(4)  -> first PW as string (meinpasswort-1)
// xx.i(21) -> second IP as string
// xx.s(25) -> second PW

import (
	"bytes"
	"fmt"
	"math/rand"
	"os"
	"os/exec"
	"strings"

	"github.com/spf13/pflag"

	"github.com/rs/zerolog/log"
	"gitlab.com/fpunkts/zlog"
)

const blockSize = 32 // max size for 2 strings

var (
	offsets = []byte{5, 7, 11, 17, 19}
	//buffer  = strings.Builder{}
	buffer = bytes.Buffer{}
	//oindex  = 0
	verbose = 2

	currentPad = 1 + len(offsets)
)

func addbyte(b byte) {
	oindex := buffer.Len()
	table := byte((b + offsets[oindex%len(offsets)]) & 0xff)
	log.Trace().Int("pos", buffer.Len()).Uint8("byte", b).Uint8("table", table).Msg("Adding byte")
	buffer.WriteByte(table)
	//oindex++
}

func addstring(s string) {
	log.Debug().Str("str", s).Msg("Adding string")
	for _, c := range s {
		addbyte(byte(c))
	}
	addbyte(0)
}

func pad() {
	currentPad += blockSize
	if buffer.Len() >= currentPad {
		log.Fatal().Int("size", buffer.Len()).Int("maxsize", currentPad).Msg("Strings to long, reduce size (change code)")
	}
	log.Trace().Int("n", currentPad-buffer.Len()).Msg("Padding bytes")
	for buffer.Len() < currentPad {
		b := rand.Intn(255)
		buffer.WriteByte(byte(b))
	}
}

func decode(fname string) {
	mod := strings.TrimSuffix(fname, ".py")
	cmd := fmt.Sprintf("import %s; print(%s.s(0), %s.s(32))", mod, mod, mod)
	log.Debug().Str("cmd", cmd).Msg("Going to run python command")
	out, err := exec.Command("python3", "-c", cmd).Output()
	if err != nil {
		log.Fatal().Err(err).Str("cmd", cmd).Msg("Cannot run python")
	}
	fmt.Println(string(out))
}

func main() {
	pflag.CountVarP(&verbose, "verbose", "v", "verbose messages")
	outputFile := pflag.StringP("output", "o", "", "Output file for generated python code")
	decodeFlag := pflag.BoolP("decode", "d", false, "Decode given python file")
	writeMain := pflag.BoolP("main", "m", false, "Create main-function for testing python code")
	pflag.Parse()

	log.Logger = zlog.New()
	zlog.SetLevel(verbose)

	if *decodeFlag {
		mod := "c"
		if pflag.NArg() == 1 {
			mod = pflag.Arg(0)
		}
		decode(mod)
		return
	}

	buffer.WriteByte(byte(len(offsets)))
	for _, o := range offsets {
		buffer.WriteByte(o)
	}

	if pflag.NArg() == 0 {
		log.Error().Msg("Need at least two arguments, use like hidepw  ssid-1 pw-1  ssid-2 pw-2")
		return
	}
	for i, arg := range pflag.Args() {
		//if isip(arg) {
		//	addip(arg)
		//	continue
		//}
		addstring(arg)
		if i%2 == 1 {
			pad()
		}
	}

	// write Python code

	fd := os.Stdout

	if *outputFile != "" {
		log.Info().Str("file", *outputFile).Msg("Writing Python outputfile")
		f, err := os.Create(*outputFile)
		if err != nil {
			log.Error().Err(err).Str("name", *outputFile).Msg("Cannot generate output file")
		}
		fd = f
	}

	//b := buffer.Bytes()
	//fmt.Printf("s = %q\n", buffer.Bytes())
	fmt.Fprintf(fd, "b = bytearray((")
	comma := ""
	for _, b := range buffer.Bytes() {
		fmt.Fprintf(fd, "%s%d", comma, b)
		comma = ", "
	}
	fmt.Fprintf(fd, "))\n")
	//fmt.Printf("s = %b\n", buffer.Bytes())

	detab := func(s string) string { return strings.ReplaceAll(s, "\t", "    ") }
	if *outputFile != "" {
		fd.WriteString(detab(pyCode))
		if *writeMain {
			fd.WriteString(detab(mainCode))
		}
	}
	for i, c := 0, 0; i < currentPad-blockSize; i += blockSize {
		fmt.Printf("# use     s(%3d)   # %16s %s\n", i, pflag.Arg(c), pflag.Arg(c+1))
		c += 2
	}
}

const (
	pyCode = `
ni = b[0]

def _s(o):
	r = ''
	o += ni
	while True:
        o += 1
        c = b[o] - b[(o)%ni+1]
		#print('# Getting @{:2d}: {:3d} -> {:3d} {:3d} {}'.format(o, b[o], c, c & 0xff, chr(c&0xff)))
		if c == 0:
			return r, o-ni
		r = r+chr(c&0xff)

def s(n):
    a, b = _s(n)
	#print('#   GOT {} {}'.format(b, a))
	c, _ = _s(b)
	return a, c
`
	mainCode = `
if __name__ == '__main__':
    print('block is {} bytes'.format(len(b)))
    print(s(0))
    print(s(32))
`
)
