#!/bin/nu

def main [fname: string] {
	cat $"./data/($fname).abnf" | 
	lines -s |
	where { |x| str starts-with "$WORD"} |
	str replace "\\{.*\\}" "" |
	str replace "\\$WORD\\_\\S* = " "" |
	str replace "\\(" "" -a | 
	str replace "\\)" "" -a |
	str replace ";" "" -a |
	str replace "\\s" "" -a |
	str replace "\\|" "\n" -a |
	save $"./data/($fname).txt" --force
}
