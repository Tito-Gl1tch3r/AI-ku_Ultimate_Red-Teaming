package main

import (
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"

	"github.com/karlmcguire/dump"
)

func index(d *dump.Dump) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var (
			data []byte
			err  error
		)

		if data, err = d.MarshalJSON(); err != nil {
			panic(err)
		}

		w.Write(data)
	}
}

func add(d *dump.Dump) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var (
			id  int
			err error
		)

		if id, err = d.Add(
			&Post{
				Name: r.FormValue("name"),
				Body: r.FormValue("body"),
			},
		); err != nil {
			panic(err)
		}

		w.Write([]byte(fmt.Sprintf("%d", id)))
	}
}

func get(d *dump.Dump) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var (
			bigId   int64
			id      int
			p       *Post
			postOut []byte
			err     error
		)

		if bigId, err = strconv.ParseInt(
			r.FormValue("id"),
			10,
			32,
		); err != nil {
			panic(err)
		}

		id = int(bigId)

		if err = d.View(func(items []dump.Item) error {
			if id > len(items) {
				return errors.New("woooops")
			}
			p = items[id].(*Post)
			return nil
		}); err != nil {
			panic(err)
		}

		if postOut, err = p.MarshalJSON(); err != nil {
			panic(err)
		}

		w.Write(postOut)
	}
}

func main() {
	var (
		d   *dump.Dump
		err error
	)

	if d, err = dump.NewDump(
		"posts.db",
		dump.PERSIST_WRITES,
		dump.Type{"main.Post", &Post{}},
	); err != nil {
		panic(err)
	}

	if err = d.Load(); err != nil {
		// io.EOF just means it is empty
		if err != io.EOF {
			panic(err)
		}
	}

	http.HandleFunc("/", index(d))
	http.HandleFunc("/add", add(d))
	http.HandleFunc("/get", get(d))

	println("listening on :8080")
	if err = http.ListenAndServe(":8080", nil); err != nil {
		panic(err)
	}
}
