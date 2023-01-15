package main

import (
	"bytes"
	"fmt"
	"io/fs"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"github.com/fpunkt/zlog"
	"github.com/rs/zerolog/log"
	"github.com/spf13/pflag"

	toml "github.com/pelletier/go-toml"
)

var libdir, ipstring string

var options = struct {
	verbose int
	dryrun  bool
	force   bool
	nolup   bool
	ip      string
}{}

const (
	importfile   = ".imports"
	ipfile       = ".espip"
	lastsyncfile = ".lastsync"
)

func main() {
	// if err := os.Chdir(os.ExpandEnv("${HOME}/Projects/fpunkts/micropy/devices/test/pwm")); err != nil {
	// 	log.Fatal().Err(err).Msg("Fatal error")
	// }
	pflag.CountVarP(&options.verbose, "verbose", "v", "verbose messages")
	pflag.BoolVarP(&options.dryrun, "dryrun", "d", false, "compile but don't upload file")
	pflag.BoolVarP(&options.force, "force", "f", false, "Force upload of all files (ignore .lastsync)")
	pflag.BoolVarP(&options.nolup, "no-lup", "l", false, "Don't overwrite lup.py file (copy last upload date to ESP)")
	pflag.StringVarP(&options.ip, "ip", "i", "", "IP to use, ignore .espip file")
	pflag.Parse()

	zlog.InitL(options.verbose)

	//if err := os.Chdir("../devices/test/pingmachine/"); err != nil {
	//	log.Fatal().Err(err).Send()
	//}

	starttime := time.Now()

	dependencies, err := readDependencies()
	if err != nil {
		log.Fatal().Err(err).Msg("Cannot read dependencies")
	}
	// cleanup - remove empty lines and duplicates
	var dd []string
	for _, d := range dependencies {
		if d == "" || options.nolup && d == "lup.py" {
			continue
		}
		dd = append(dd, d)
	}
	dependencies = dd

	//fmt.Printf("dependencies: %v\n", dependencies)
	//if err == nil {
	//	os.Exit(0)
	//}

	log.Trace().Int("dependencies", len(dependencies)).Strs("imports", dependencies).Msg("Loaded dependencies")

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

	libdir = locateLibdir()
	//bindir = filepath.Clean(libdir + "../bin/")
	log.Trace().
		Str("libdir", libdir).
		//Str("bindir", bindir).
		Msg("Located libdir")
	//fmt.Printf("bindir = %s, libdir = %s\n", bindir, libdir)

	here, err := os.Getwd()
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
	if err := os.Chdir(libdir); err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}

	if err := os.Chdir(here); err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}

	var lastupload time.Time
	if !options.force {
		if s, err := os.Stat(lastsyncfile); err == nil {
			lastupload = s.ModTime()
		}
	}
	//var changed []string

	changed := compileFiles(libdir, dependencies, lastupload)

	// check files in current directory
	direntries, err := os.ReadDir(".")
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
	var files []string
	for _, f := range direntries {
		fname := f.Name()
		if strings.HasSuffix(fname, ".py") {
			files = append(files, fname)
		}
	}
	if !options.nolup {
		const lastuploadfile = "lup.py"
		if fd, err := os.Create(lastuploadfile); err != nil {
			log.Error().Err(err).Str("file", lastuploadfile).Msg("Cannot create file last upload file")
		} else {
			fmt.Fprintf(fd, "T = %d\n", time.Now().Unix())
			fd.Close()
			log.Info().Str("file", lastuploadfile).Msg("File created")
			defer os.Remove(lastuploadfile)
			// append file if not already included in list (might be leftover from failed run before)
			doapp := true
			for _, s := range files {
				if s == lastuploadfile {
					doapp = false
					break
				}
			}
			if doapp {
				files = append(files, lastuploadfile)
			}
		}
	}
	//	if b, err := os.ReadFile(lastuploadfile); err != nil {
	//		log.Error().Err(err).Str("file", lastuploadfile).Msg("Cannot read file")
	//	} else {
	//		fmt.Printf("lup: %q\n", string(b))
	//	}

	files = compileFiles(".", files, lastupload)
	changed = append(changed, files...)

	if len(changed) == 0 {
		fmt.Printf("# no files to upload since %s\n", lastupload.String())
		return
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
	currentdir, _ := os.Getwd()

	// augment changed files by command line arguments
	if pflag.NArg() > 0 {
		project, _ := os.ReadDir(".")
		lib, _ := os.ReadDir(libdir)

		ff := func(f string, dir []fs.DirEntry) string {
			for _, d := range dir {
				if strings.HasPrefix(d.Name(), f) {
					return d.Name()
				}
			}
			return ""
		}
		for _, f := range pflag.Args() {
			if s := ff(f, project); s != "" {
				fmt.Printf("Got %q for %q\n", s, f)
				changed = append(changed, s)
			}
			if s := ff(f, lib); s != "" {
				fmt.Printf("Got %q for %q\n", s, f)
				changed = append(changed, s)
			}
		}
	}

	//fmt.Println(changed)

	for _, file := range changed {
		s, err := os.Stat(file)
		if err != nil {
			log.Fatal().Err(err).Msg("Cannot stat file")
		}
		//fmt.Printf("%20s: %s - %s - %T\n", file, s.ModTime(), lastupload, s.ModTime().Before(lastupload))
		// HUH? We already checked that?
		if s.ModTime().Before(lastupload) {
			continue
		}
		relp := file
		//fmt.Printf("relp=%s, cd=%s\n", relp, currentdir)
		if currentdir != "" {
			relp, err = filepath.Rel(currentdir, file)
			if err != nil {
				relp = file
			}
		}
		log.Info().Str("file", relp).Msg("Uploading file")
		if options.dryrun {
			log.Debug().Msg("Not Uploading because of dryrun")
		} else {
			upload(file)
		}
	}

	log.Info().
		Int("nfiles", len(changed)).
		Str("duration", time.Since(starttime).Truncate(time.Millisecond).String()).
		Msg("Uploaded files")

	if !options.dryrun {
		run("touch " + lastsyncfile)
	}

	//	fmt.Println(lines(string(dependencies)))
	//	fmt.Println(changed)

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
	_, serr, err := run(libdir + "/../webrepl/webrepl_cli.py -p x " + fname + " " + ipstring + ":")
	if serr != "" {
		fmt.Printf("# ERROR - uploading %s: %s\n", fname, serr)
	}
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
}

// run shell command, return err, stdout, stderr
func run(command string) (string, string, error) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd := exec.Command("/bin/sh", "-c", command)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	return stdout.String(), stderr.String(), err
}

// compile files in directory if they are newer than timestamp
func compileFiles(directory string, files []string, timestamp time.Time) []string {
	var changed []string
	for _, basename := range files {
		fullname := filepath.Join(directory, basename)
		_, err := os.Stat(fullname)
		if err != nil {
			log.Fatal().Err(err).Msg("Fatal error")
		}
		//compiled := compile(fullname, timestamp)
		//s, err := os.Stat(compiled)
		//if err != nil {
		//	log.Fatal().Err(err).Msg("Fatal error")
		//}
		compiled, newts := compile(fullname)
		if newts.After(timestamp) {
			log.Debug().
				Str("file", filepath.Base(compiled)).
				Str("last", ts(timestamp)).
				Str("modtime", ts(newts)).
				Msg("File has changed since last upload")
			changed = append(changed, compiled)
		}
	}
	return changed
}

// do not compile these files
var exclude = map[string]struct{}{
	"main.py": {},
}

func ts(t time.Time) string { return t.Format("2006-01-02 15:04:05") }
func mustModTime(fname string) time.Time {
	s, err := os.Stat(fname)
	if err != nil {
		log.Fatal().Err(err).Str("file", fname).Msg("Fatal error")
	}
	return s.ModTime()
}

// compile file if outdated
func compile(fname string) (string, time.Time) {
	ftime := mustModTime(fname)
	if _, ok := exclude[filepath.Base(fname)]; ok {
		log.Trace().Str("file", fname).Msg("Ignoring file from excludes")
		return fname, ftime
	}
	//dir := filepath.Dir(fname)
	here, err := os.Getwd()
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
	defer os.Chdir(here)

	outfile := strings.TrimSuffix(fname, ".py") + ".mpy"
	stat, err := os.Stat(outfile)
	if err == nil {
		log.Trace().
			Str("file", filepath.Base(fname)).
			Str("py", ts(ftime)).
			Str("mpy", ts(stat.ModTime())).
			Msg("Compiled file exists")
	}
	if err == nil && stat.ModTime().After(ftime) {
		log.Trace().Str("file", fname).Msg("No need to compile because binary is newer")
		// fmt.Printf("# no need to compile %s\n", fname)
		return outfile, stat.ModTime()
	}
	log.Info().Str("file", fname).Msg("Compiling")
	modTime := "new"
	if stat != nil {
		ts(stat.ModTime())
	}
	log.Trace().
		Str("file", filepath.Base(fname)).
		Str("ts", ts(ftime)).
		Str("mod", modTime).
		Msg("Compiling")
	sout, serr, err := run("mpy-cross " + fname)
	if err != nil {
		log.Fatal().Err(err).Msg("Fatal error")
	}
	if serr != "" {
		log.Error().Str("err", serr).Str("file", fname).Msg("Compile error")
		//fmt.Printf("# ERROR comiling %s: %s\n", fname, serr)
	}
	if sout != "" {
		log.Warn().Str("file", fname).Str("compiler", sout).Msg("Compiler output")
		//fmt.Printf("# comiling %s: %s\n", fname, sout)
	}
	return strings.TrimSuffix(fname, ".py") + ".mpy", time.Now()
}

func readDependencies() ([]string, error) {
	if fname := findToml(); fname != "" {
		if _, err := os.Stat(importfile); err != nil {
			return readTOML(fname)
		}
	}
	if _, err := os.Stat(importfile); err == nil {
		log.Debug().Str("file", importfile).Msg("Reading dependencies from dependencies input file")
		b, err := os.ReadFile(importfile)
		if err != nil {
			return nil, err
		}
		return strings.Split(string(b), "\n"), nil
	}
	log.Debug().Str("file", importfile).Msg("Scanning files for dependencies")
	return parsePythonfiles()
}

type importpath map[string]string

func parsePythonfiles() ([]string, error) {
	seen := importpath{}

	mainfiles := dirtomap(".")
	libdir := locateLibdir()
	libfiles := dirtomap(libdir)

	for mainfile := range mainfiles {
		recursiveScanImports(mainfile, libdir, mainfiles, libfiles, seen)
	}

	delete(seen, "main")

	var out []string
	for _, k := range seen {
		out = append(out, k)
	}
	return out, nil
}

func recursiveScanImports(importname, libdir string, mainfiles, libfiles, seen importpath) {
	if _, ok := seen[importname]; ok {
		return
	}
	log.Trace().Str("file", importname).Msg("Scanning file")
	var path string
	var ok bool
	if path, ok = mainfiles[importname]; ok {
		log.Trace().Str("import", importname).Msg("Found mainfile")
	} else if path, ok = libfiles[importname]; ok {
		log.Trace().Str("import", importname).Msg("Found libfile")
	} else {
		log.Trace().Str("import", importname).Msg("Not found, assuming system file")
		return
	}
	seen[importname] = importname + ".py"
	imports := findImportsInPythonfile(path)
	for _, f := range imports {
		log.Trace().Str("import", f).Msg("Nested import")
		recursiveScanImports(f, libdir, mainfiles, libfiles, seen)
	}
}

func dirtomap(path string) importpath {
	files, err := os.ReadDir(path)
	if err != nil {
		log.Fatal().Err(err).Str("path", path).Msg("Cannot read directory")
	}
	m := importpath{}
	if path == "." || path == "./" {
		path = ""
	} else {
		if !strings.HasSuffix(path, "/") {
			path += "/"
		}
	}

	for _, f := range files {
		fname := f.Name()
		if s, err := filepath.EvalSymlinks(fname); err == nil {
			//fmt.Printf("Found Symlink: %s -> %s\n", fname, s)
			fname = filepath.Base(s)
		}
		lower := strings.ToLower(fname)
		if !strings.HasSuffix(lower, ".py") {
			log.Trace().Str("path", f.Name()).Msg("Skipping non-python file")
			continue
		}
		importname := strings.TrimSuffix(lower, ".py")
		m[importname] = path + f.Name()
	}
	return m
}

func findImportsInPythonfile(fname string) []string {
	txt, err := os.ReadFile(fname)
	if err != nil {
		log.Fatal().Err(err).Str("fname", fname).Msg("Cannot read file")
	}
	//	rx := regexp.MustCompile(`^import\s+([^#].*).*`)
	rx := regexp.MustCompile(`import\s+([^#].*).*`)
	m := rx.FindAllStringSubmatch(string(txt), -1)
	if len(m) == 0 {
		log.Trace().Str("file", fname).Msg("No imports")
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

func findToml() string {
	tomlfiles, err := filepath.Glob("*.toml")
	if len(tomlfiles) == 0 || err != nil {
		return ""
	}
	if len(tomlfiles) == 1 {
		return tomlfiles[0]
	}

	log.Warn().Int("nfiles", len(tomlfiles)).Msg("Need exactly one toml file, found more")
	return ""
	//		s := "none"
	//		if len(tomlfiles) > 1 {
	//			s = fmt.Sprintf("%d (%v)", len(tomlfiles), tomlfiles)
	//		}
	//		return nil, fmt.Errorf("need %s or exactly one .toml file, found %s", importfile, s)

}

func readTOML(fname string) ([]string, error) {
	log.Debug().Str("file", fname).Msg("Reading dependencies from TOML input file")
	config, err := toml.LoadFile(fname)
	if err != nil {
		return nil, err
	}
	// retrieve data directly
	imports := config.Get("dependencies.libfiles")
	if ia, ok := imports.([]interface{}); ok {
		var out []string
		for _, i := range ia {
			if s, ok := i.(string); ok {
				out = append(out, s)
			} else {
				return nil, fmt.Errorf("item is not a string: %T - %v", i, i)
			}

		}
		return out, nil
	}
	//if len(imports) == 0 {
	//	return nil, fmt.Errorf("File %s does not contain a [depencencies.libfiles] section", tomlfiles[0])
	//}
	fmt.Printf("imports: %T %v\n", imports, imports)
	return nil, nil
}
