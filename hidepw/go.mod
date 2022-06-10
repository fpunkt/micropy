module hidepw

go 1.17

replace gitlab.com/fpunkts/zlog => ../../zlog

require (
	github.com/rs/zerolog v1.26.0
	github.com/spf13/pflag v1.0.5
	gitlab.com/fpunkts/zlog v0.0.0-00010101000000-000000000000
)

require github.com/pkg/errors v0.9.1 // indirect
