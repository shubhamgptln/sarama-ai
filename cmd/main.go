package cmd

import (
	"flag"
	"log"
)

func Main() {
	port := flag.String("port", "8080", "Server port")
	flag.Parse()

	log.Println("Sarama AI Server starting...")
	StartServer(*port)
}
