package main

import (
	"bytes"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/fpunkt/zlog"
	toml "github.com/pelletier/go-toml/v2"
	"github.com/rs/zerolog/log"
	"github.com/spf13/pflag"
	"golang.org/x/exp/maps"
)

var ipstring string

var options = struct {
	verbose     int
	dryrun      bool
	force       bool
	nolup       bool
	ip          string
	initialBoot bool
	reboot      bool
	rebootCanID int
	cansrv      string
	igoredfiles []string
	libdir      string
	extlibdir   string
	builddir    string
}{}

const (
	//importfile   = ".imports"
	ipfile       = ".espip"
	lastsyncfile = ".lastsync"
)

func main() {
	pflag.CountVarP(&options.verbose, "verbose", "v", "verbose messages")
	pflag.BoolVarP(&options.dryrun, "dryrun", "d", false, "compile but don't upload file")
	pflag.BoolVarP(&options.force, "force", "f", false, "Force upload of all files (ignore .lastsync)")
	pflag.BoolVarP(&options.nolup, "no-lup", "l", false, "Don't overwrite lup.py file (copy last upload date to ESP)")
	pflag.BoolVarP(&options.initialBoot, "initial-setup", "b", false, "Initial setup after firmware upgrade")
	pflag.BoolVarP(&options.reboot, "reboot", "r", false, "Reboot after uploading file. CAN ID is taken from TOML config file")
	pflag.IntVarP(&options.rebootCanID, "reboot-canid", "R", 0, "Reboot after uploading file, canid must be provided as argument")
	pflag.StringVarP(&options.ip, "ip", "i", "", "IP to use, ignore .espip file")
	pflag.StringVarP(&options.libdir, "libdir", "L", "", "Specify library directory, leave empty for auto detection")
	pflag.StringVarP(&options.extlibdir, "external-libdir", "E", "", "Specify external library directory, leave empty for auto detection")
	pflag.StringVarP(&options.builddir, "build-dir", "B", ".build", "Directory for compiler output files")
	pflag.StringVarP(&options.cansrv, "canserver", "C", "", "canserver used to send reset command")
	pflag.StringSliceVarP(&options.igoredfiles, "ignore-files", "I", []string{
		"c.py",
	}, "Ingore directories when seraching for dependencies")
	pflag.Parse()

	if options.builddir != "" && !strings.HasSuffix(options.builddir, "/") {
		options.builddir = options.builddir + "/"
	}
	if !options.dryrun && options.builddir != "" {
		if err := os.MkdirAll(options.builddir, 0700); err != nil {
			log.Fatal().Str("path", options.builddir).Msg("Cannot create build directory")
		}
	}

	if options.initialBoot {
		fmt.Println("For initial setup see     tools/initial-setup.sh")
		fmt.Println("  (basically: use ampy to upload net.mpy and c.mpy)")
		os.Exit(0)
	}

	zlog.InitL(options.verbose)

	starttime := time.Now()

	if options.libdir == "" {
		options.libdir = locateLibdir()
	}
	if options.extlibdir == "" {
		options.extlibdir = filepath.Clean(locateLibdir() + "/../extern")
	}

	var canid int
	if options.reboot {
		canid = getCanIDFromTOML()
	}

	if !options.nolup {
		const ll = "lup"
		const lastuploadfile = ll + ".py"
		if fd, err := os.Create(lastuploadfile); err != nil {
			log.Error().Err(err).Str("file", lastuploadfile).Msg("Cannot create file last upload file")
		} else {
			fmt.Fprintf(fd, "T = %d\n", time.Now().Unix())
			fd.Close()
			log.Info().Str("file", lastuploadfile).Msg("File created")
			defer os.Remove(lastuploadfile)
			defer os.Remove(ll + ".mpy")
		}
	}

	dependencies, err := parsePythonfiles()
	// the main.py file must not be compiled
	mainfile := dependencies["main"]
	delete(dependencies, "main")

	if err != nil {
		log.Fatal().Err(err).Msg("Cannot read dependencies")
	}

	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}

	if options.ip == "" {
		if ips, err := os.ReadFile(ipfile); err != nil {
			log.Fatal().Err(err).Msg("Fatal error")
		} else {
			ipstring = strings.TrimSpace(string(ips))
		}
	} else {
		switch len(strings.Split(options.ip, ".")) {
		case 1:
			ipstring = "192.168.178." + options.ip
		case 3:
			ipstring = options.ip
		default:
			log.Fatal().Str("ip", options.ip).Msg("Bad IP string")
		}
	}

	var lastupload time.Time
	if !options.force {
		if s, err := os.Stat(lastsyncfile); err == nil {
			lastupload = s.ModTime()
		}
	}
	//var changed []string

	if options.verbose > 3 {
		dependencies.dump(os.Stdout)
	}
	changed := compileFiles(dependencies, lastupload, pflag.Args())

	if lastupload.IsZero() || mainfile.mtime.After(lastupload) {
		mainfile.compilename = mainfile.fullname
		changed = append(changed, mainfile)
	}

	if len(changed) == 0 {
		log.Info().Str("lastupload", lastupload.String()).Msg("# no files to upload since")
		//return
	}

	iplogger := log.With().Str("host", ipstring).Logger()
	if addr, err := net.LookupIP(ipstring); err != nil {
		iplogger.Error().Err(err).Msg("Cannot lookup IP for host")
	} else {
		iplogger = iplogger.With().Str("ip4", addr[0].String()).Logger()
		if len(addr) > 1 {
			iplogger = iplogger.With().Str("ip6", addr[1].String()).Logger()
		}
	}
	iplogger.Info().Int("nfiles", len(changed)).Msg("Uploading files")

	//fmt.Println(changed)

	for _, file := range changed {
		log.Info().Str("file", file.compilename).Msg("Uploading file")
		if options.dryrun {
			log.Debug().Msg("Not Uploading because of dryrun")
		} else {
			upload(file.compilename)
		}
	}

	log.Info().
		Int("nfiles", len(changed)).
		Str("duration", time.Since(starttime).Truncate(time.Millisecond).String()).
		Msg("Uploaded files")

	if !options.dryrun {
		run("touch " + lastsyncfile)
	}

	switch {
	case canid > 0:
		reboot(canid)
	case options.rebootCanID > 0:
		reboot(options.rebootCanID)
	}
}

func reboot(canid int) {
	l := log.Info()
	cmd := []string{}
	if options.cansrv != "" {
		cmd = append(cmd, "-C")
		cmd = append(cmd, options.cansrv)
		l = l.Str("cansrv", options.cansrv)
	}
	cmd = append(cmd, "reset", "-c", fmt.Sprint(canid))
	l.Str("canid", fmt.Sprintf("0x%03x", canid)).Msg("Sending reboot")
	if options.verbose > 3 {
		log.Trace().Str("cmd", strings.Join(cmd, " ")).Msg("Running command")
	}
	if err := exec.Command("cantool", cmd...).Run(); err != nil {
		log.Error().Err(err).Msg("Cannot reset device")
	}
}

func locateLibdir() string {
	cwd, err := os.Getwd()
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot read cwd")
	}
	abs, err := filepath.Abs(cwd)
	if err != nil {
		log.Fatal().Err(err).Str("cwd", abs).Msg("Cannot get abs path")
	}
	var libdir string
	for i := 1; i < 7; i++ {
		p := filepath.Clean(abs + strings.Repeat("/..", i) + "/lib")
		log.Trace().Str("dir"+"/fsmpylibdir.md", p).Msg("Looking for libdir")
		if s, err := os.Stat(p); err != nil || !s.IsDir() {
			//fmt.Printf("p: %s, e: %s\n", p, err)
			continue
		}
		libdir = p
		break
	}
	if libdir == "" {
		log.Fatal().Msg("Cannot find libdir")
	}
	return libdir
}

func upload(fname string) {
	if 1 == 0 {
		return
	}
	_, serr, err := run(options.libdir + "/../webrepl/webrepl_cli.py -p x " + fname + " " + ipstring + ":")
	if serr != "" {
		fmt.Printf("# ERROR - uploading %s: %s\n", fname, serr)
	}
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
}

type file struct {
	name        string
	mtime       time.Time // modtime of the sourcefile
	fullname    string    // follows symlinks
	importname  string    // striped path and extension
	compilename string    // importname + .mpy
	compiletime time.Time
}

// run shell command, return err, stdout, stderr
func run(command string) (string, string, error) {
	if options.dryrun {
		log.Debug().Str("cmd", command).Msg("dryrun")
		return "", "", nil
	}
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd := exec.Command("/bin/sh", "-c", command)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	return stdout.String(), stderr.String(), err
}

// compile files in directory if they are newer than timestamp
func compileFiles(files filemap, timestamp time.Time, force []string) []*file {
	if len(force) != 0 {
		log.Fatal().Strs("force", force).Msg("Force not implemented")
	}
	var changed []*file
	for _, f := range files {
		if _, ok := exclude[f.importname]; ok {
			log.Trace().Str("file", f.name).Msg("Ignoring file from excludes")
			continue
		}
		if timestamp.IsZero() {
		} else {
			stat, err := os.Stat(f.compilename)
			if err == nil && stat.ModTime().After(f.mtime) {
				log.Trace().Str("file", f.name).Msg("No need to compile because binary is newer")
				// fmt.Printf("# no need to compile %s\n", fname)
				f.compiletime = stat.ModTime()
				continue
			}
			var reason string
			if err != nil {
				reason = "newfile"
			} else {
				reason = "outdated"
			}
			log.Info().Str("file", f.fullname).Str("object", f.compilename).Str("reason", reason).Msg("Compiling")
		}
		compiled := compile(f)

		log.Debug().
			Str("file", filepath.Base(compiled.name)).
			Str("lastupload", ts(timestamp)).
			Str("modtime", ts(compiled.compiletime)).
			Msg("File has changed since last upload")
		changed = append(changed, compiled)
	}
	return changed
}

// do not compile these files
var exclude = map[string]struct{}{
	"main.py": {},
}

func ts(t time.Time) string { return t.Format("2006-01-02 15:04:05") }

//func mustModTime(fname string) time.Time {
//	s, err := os.Stat(fname)
//	if err != nil {
//		log.Fatal().Err(err).Str("file", fname).Msg("Fatal error")
//	}
//	return s.ModTime()
//}

// Update f.compiledtime and compile file if non-existing or outdated, return nil when file is OK.
func compile(f *file) *file {
	//	log.Trace().
	//		Str("file", f.name).
	//		Str("ts", ts(f.mtime)).
	//		Str("mod", modTime).
	//		Msg("Compiling")
	cmd := fmt.Sprintf("mpy-cross -o %s %s", f.compilename, f.fullname)
	sout, serr, err := run(cmd)
	if err != nil {
		log.Fatal().Err(err).Str("cmd", cmd).Msg("Cannot compile")
	}
	if serr != "" {
		log.Error().Str("err", serr).Str("file", f.name).Msg("Compile error")
		//fmt.Printf("# ERROR comiling %s: %s\n", fname, serr)
	}
	if sout != "" {
		log.Warn().Str("file", f.name).Str("compiler", sout).Msg("Compiler output")
		//fmt.Printf("# comiling %s: %s\n", fname, sout)
	}
	f.compiletime = time.Now()
	return f
}

//func readDependencies() ([]string, error) {
//	if fname := findToml(); fname != "" {
//		if _, err := os.Stat(importfile); err != nil {
//			dep, err := readTOML(fname)
//			if err != nil {
//				log.Error().Err(err).Str("file", fname).Msg("Error in condiguration file")
//			}
//			if err == nil && len(dep) > 0 {
//				return dep, nil
//			}
//		}
//	}
//	if _, err := os.Stat(importfile); err == nil {
//		log.Debug().Str("file", importfile).Msg("Reading dependencies from dependencies input file")
//		b, err := os.ReadFile(importfile)
//		if err != nil {
//			return nil, err
//		}
//		return strings.Split(string(b), "\n"), nil
//	}
//	log.Debug().Str("file", importfile).Msg("Scanning files for dependencies (dependeciy file not found)")
//	return
//}

type filemap map[string]*file

func (fm filemap) dump(fd io.Writer) {
	fmt.Fprintf(fd, "%d entries\n", len(fm))
	for _, f := range fm {
		f.dump(fd)
	}
}

//var ignorefiles = map[string]struct{}{}

func parsePythonfiles() (filemap, error) {
	//	for _, ignore := range options.igoredfiles {
	//		ignorefiles[ignore] = struct{}{}
	//	}

	files := map[string]*file{}
	readdir(".", files)
	mainfiles := maps.Keys(files)
	readdir(options.libdir, files)
	readdir(options.extlibdir, files)
	seen := filemap{}

	for _, sourcefile := range mainfiles {
		recursiveScanImports(sourcefile, files, seen)
	}

	log.Debug().Strs("files", maps.Keys(seen)).Msg("Scanned dependencies")
	return seen, nil
}

// parse file and all referenced files for import statements, return result in parameter map "seen"
func recursiveScanImports(importname string, files, seen filemap) {
	if _, ok := seen[importname]; ok {
		log.Trace().Str("file", importname).Msg("Scanning for imports: already seen")
		return
	}

	lg := log.Trace().Str("file", importname)
	var f *file
	var ok bool
	if f, ok = files[importname]; ok {
		lg = lg.Str("type", "main")
		//	} else if f, ok = libfiles[importname]; ok {
		//		lg = lg.Str("type", "lib")
	} else {
		lg.Msg("skippingfile - not found, assuming systemfile")
		return
	}
	lg.Msg("Scanning file")
	seen[importname] = f
	imports := f.findImports()
	log.Trace().Strs("found", imports).Str("file", importname).Msg("Scan Imports")
	for _, f := range imports {
		if _, ok := seen[f]; ok {
			log.Trace().Str("import", f).Msg("Already seen - skipping")
			//continue
		}
		log.Trace().Str("import", f).Msg("Nested import")
		recursiveScanImports(f, files, seen)
	}
}

// scan directory for python files
func readdir(path string, filemap map[string]*file) {
	// not using os.listdir() because we need to resolve symlinks
	files, err := os.ReadDir(path)
	if err != nil {
		log.Fatal().Err(err).Str("path", path).Msg("Cannot read directory")
	}
	//	m := map[string]*file{}

	var nicepath string
	switch {
	case path == "." || path == "./":
	case !strings.HasSuffix(path, "/"):
		nicepath = path + "/"
	default:
		nicepath = path
	}

	for _, f := range files {
		fname := f.Name()
		lower := strings.ToLower(fname)
		if !strings.HasSuffix(lower, ".py") {
			log.Trace().Str("path", fname).Msg("Skipping non-python file")
			continue
		}
		importname := strings.TrimSuffix(lower, ".py")
		cn := options.builddir + importname + ".mpy"
		ff := file{name: fname, fullname: nicepath + fname, importname: importname, compilename: cn}
		if info, err := f.Info(); err != nil {
			log.Error().Err(err).Str("path", fname).Msg("Cannot stat")
			continue
		} else {
			ff.mtime = info.ModTime()
		}
		if s, err := filepath.EvalSymlinks(fname); err == nil {
			log.Trace().Str("file", fname).Str("linkto", s).Msg("Found symlink")
			// overwrite timestamp with timestamp from symlink
			i, err := os.Stat(s)
			if err != nil {
				log.Error().Err(err).Str("file", fname).Str("link", s).Msg("Cannot read info for symlink")
			}
			ff.mtime = i.ModTime()
			ff.fullname = s
		}
		if f, ok := filemap[ff.importname]; ok {
			log.Error().Str("import", ff.importname).Str("source1", f.fullname).Str("source2", ff.fullname).Msg("Import exists in multiple places")
		}
		filemap[ff.importname] = &ff
	}
	log.Trace().Str("path", path).Strs("files", maps.Keys(filemap)).Msg("Read directory")
}

func (f *file) findImports() []string {
	txt, err := os.ReadFile(f.fullname)
	if err != nil {
		s, err := filepath.EvalSymlinks(f.fullname)
		log.Trace().Err(err).Str("file", f.fullname).Str("linkto", s).Msg("Found symlink")
		log.Fatal().Err(err).Str("fname", f.fullname).Msg("Cannot read file")
	}
	//	rx := regexp.MustCompile(`^import\s+([^#].*).*`)
	rx := regexp.MustCompile(`import\s+([^#].*).*`)
	m := rx.FindAllStringSubmatch(string(txt), -1)
	if len(m) == 0 {
		log.Trace().Str("file", f.fullname).Msg("No imports")
		return nil
	}
	var ff []string
	for _, f := range m {
		if len(f) != 2 {
			log.Warn().Int("n", len(f)).Strs("matches", f).Msg("Found")
			continue
		}
		ff = append(ff, f[1])
	}
	return ff
}

func (f *file) dump(fd io.Writer) {
	fmt.Fprintf(fd, "  n: %s, f: %s, c: %s\n", f.name, f.fullname, f.compilename)
}

func getCanIDFromTOML() int {
	tomlfiles, err := filepath.Glob("*.toml")
	switch {
	case err != nil:
		log.Fatal().Err(err).Msg("Cannot glob for *.toml in current directory")
	case len(tomlfiles) == 0:
		return parseMainDotPy()
	case len(tomlfiles) != 1:
		log.Fatal().Strs("files", tomlfiles).Int("found", len(tomlfiles)).Msg("Found multiple .toml files, need exactly one")
	}
	fname := tomlfiles[0]
	log.Debug().Str("file", fname).Msg("Reading dependencies from TOML input file")
	fd, err := os.Open(fname)
	if err != nil {
		log.Fatal().Err(err).Str("file", fname).Msg("Cannot open file")
	}
	data, err := io.ReadAll(fd)
	if err != nil {
		log.Fatal().Err(err).Str("file", fname).Msg("Cannot read file")
	}
	cfg := struct {
		Canid int
	}{}
	if err := toml.Unmarshal(data, &cfg); err != nil {
		l := log.Fatal()
		var derr *toml.DecodeError
		if errors.As(err, &derr) {
			// fmt.Println(derr.String())
			row, col := derr.Position()
			l = l.Int("row", row).Int("col", col)
		}
		l.Err(err).Str("file", fname).Msg("Cannot parse TOML file")
	}
	return cfg.Canid
}

func parseMainDotPy() int {
	txt, err := os.ReadFile("main.py")
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot find .toml file and cannot read main.py")
	}
	rx := regexp.MustCompile(`(?m)^\s*board.CANID\s*=\s*([^#\n\s]*)`)
	m := rx.FindAllStringSubmatch(string(txt), 2)
	if len(m) != 1 || len(m[0]) != 2 {
		log.Fatal().Err(err).Msg("Cannot find .toml file and cannot find board.CANID = xxxx in main.py")
	}
	i, err := strconv.ParseInt(m[0][1], 0, 14)
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot find .toml file and parse board.CANID = xxxx in main.py")
	}
	//fmt.Printf("%v\n", i)
	//os.Exit(0)
	return int(i)
}
