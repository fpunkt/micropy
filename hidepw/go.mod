module hidepw

go 1.17

replace github.com/fpunkt/zlog => ../../../../github.com/fpunkt/zlog/

require (
	github.com/fpunkt/zlog v0.0.0-00010101000000-000000000000
	github.com/rs/zerolog v1.26.0
	github.com/spf13/pflag v1.0.5
)

require github.com/pkg/errors v0.9.1 // indirect
