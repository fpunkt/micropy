package main

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

var libdir, bindir, ipstring string

const (
	importfile   = ".imports"
	ipfile       = ".espip"
	lastsyncfile = ".lastsync"
)

func main() {
	// if err := os.Chdir(os.ExpandEnv("${HOME}/Projects/fpunkts/micropy/devices/test/pwm")); err != nil {
	// 	log.Fatal(err)
	// }

	starttime := time.Now()

	dependencies, err := os.ReadFile(importfile)
	if err != nil {
		log.Fatal(err)
	}

	if ips, err := os.ReadFile(ipfile); err != nil {
		log.Fatal(err)
	} else {
		ipstring = strings.TrimSpace(string(ips))
	}
	execdir, err := os.Executable()
	if err != nil {
		log.Fatal(err)
	}

	if strings.HasPrefix(execdir, "/var/") {
		bindir = os.ExpandEnv("${HOME}/Projects/fpunkts/micropy/bin")
	} else {
		bindir = filepath.Dir(execdir)
	}
	libdir = filepath.Clean(bindir + "/../lib")
	//fmt.Printf("bindir = %s, libdir = %s\n", bindir, libdir)

	here, err := os.Getwd()
	if err != nil {
		log.Fatal(err)
	}
	if err := os.Chdir(libdir); err != nil {
		log.Fatal(err)
	}

	//err, sout, serr := run("make")
	//
	//if !strings.HasPrefix(sout, "make: Nothing to be done") {
	//	if err != nil {
	//		fmt.Printf("sout=%q, serr=%q, err=%s\n", sout, serr, err)
	//		log.Fatal(err)
	//	}
	//	if serr != "" {
	//		fmt.Printf("# make ERROR - %s\n", serr)
	//	}
	//	for _, line := range lines(sout) {
	//		fmt.Printf("# %s\n", line)
	//	}
	//}

	if err := os.Chdir(here); err != nil {
		log.Fatal(err)
	}

	var lastupload time.Time
	if s, err := os.Stat(lastsyncfile); err == nil {
		lastupload = s.ModTime()
	}

	//var changed []string

	changed := comileFiles(libdir, lines(string(dependencies)), lastupload)

	// check files in current directory
	direntries, err := os.ReadDir(".")
	if err != nil {
		log.Fatal(err)
	}
	var files []string
	for _, f := range direntries {
		fname := f.Name()
		if strings.HasSuffix(fname, ".py") {
			files = append(files, fname)
		}
	}
	files = comileFiles(".", files, lastupload)
	changed = append(changed, files...)

	if len(changed) == 0 {
		fmt.Printf("# no files to upload since %s\n", lastupload.String())
		return
	}

	fmt.Printf("# Uploading %d files to %s\n", len(changed), ipstring)

	for _, file := range changed {
		s, err := os.Stat(file)
		if err != nil {
			log.Fatal(err)
		}
		//fmt.Printf("%20s: %s - %s - %T\n", file, s.ModTime(), lastupload, s.ModTime().Before(lastupload))
		if s.ModTime().Before(lastupload) {
			continue
		}
		upload(file)
	}

	fmt.Printf("# Uploaded %d files in %s\n", len(changed), time.Since(starttime).Truncate(time.Millisecond).String())
	run("touch " + lastsyncfile)

	//	fmt.Println(lines(string(dependencies)))
	//	fmt.Println(changed)

}

func upload(fname string) {
	fmt.Printf("# Uploading %s\n", fname)
	if 1 == 0 {
		return
	}
	err, _, serr := run(libdir + "/../webrepl/webrepl_cli.py -p x " + fname + " " + ipstring + ":")
	if serr != "" {
		fmt.Printf("# ERROR - uploading %s: %s\n", fname, serr)
	}
	if err != nil {
		log.Fatal(err)
	}
}

// split string into lines
func lines(s string) []string {
	var out []string
	for _, line := range strings.Split(s, "\n") {
		if line != "" {
			out = append(out, line)
		}
	}
	return out
}

// run shell command, return err, stdout, stderr
func run(command string) (error, string, string) {
	var stdout bytes.Buffer
	var stderr bytes.Buffer
	cmd := exec.Command("/bin/sh", "-c", command)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()
	return err, stdout.String(), stderr.String()
}

// compile files in directory if they are newer than timestamp
func comileFiles(directory string, files []string, timestamp time.Time) []string {
	var changed []string
	for _, basename := range files {
		fullname := filepath.Join(directory, basename)
		_, err := os.Stat(fullname)
		if err != nil {
			log.Fatal(err)
		}
		compiled := compile(fullname, timestamp)
		s, err := os.Stat(compiled)
		if err != nil {
			log.Fatal(err)
		}
		if s.ModTime().After(timestamp) {
			changed = append(changed, compiled)
		}
	}
	return changed
}

// do not compile these files
var exclude = map[string]struct{}{
	"main.py": {},
}

// compile file if outdated
func compile(fname string, timestamp time.Time) string {
	if _, ok := exclude[fname]; ok {
		return fname
	}
	//dir := filepath.Dir(fname)
	here, err := os.Getwd()
	if err != nil {
		log.Fatal(err)
	}
	defer os.Chdir(here)

	outfile := strings.TrimSuffix(fname, ".py") + ".mpy"
	stat, err := os.Stat(outfile)
	if err == nil && stat.ModTime().Before(timestamp) {
		// fmt.Printf("# no need to compile %s\n", fname)
		return outfile
	}
	fmt.Printf("# compiling %s\n", fname)
	err, sout, serr := run("mpy-cross " + fname)
	if err != nil {
		log.Fatal(err)
	}
	if serr != "" {
		fmt.Printf("# ERROR comiling %s: %s\n", fname, serr)
	}
	if serr != "" {
		fmt.Printf("# comiling %s: %s\n", fname, sout)
	}
	return strings.TrimSuffix(fname, ".py") + ".mpy"
}
