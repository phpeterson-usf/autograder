#/usr/bin/env bash

_grade_complete()
{
  local cur prev

  IFS=$COMP_STUDENTS_SEP
  COMPREPLY=()
  cur=${COMP_WORDS[COMP_CWORD]}
  prev=${COMP_WORDS[COMP_CWORD-1]}

  if [ $COMP_CWORD -eq 1 ]; then
    COMPREPLY=( $(compgen -W "clone|class|exec|pull|test|upload" -- $cur) )
  elif [ $COMP_CWORD -ge 2 ]; then
    case "$prev" in
      "-s")
        COMPREPLY=( $(compgen -W "$(grade complete)" -- $cur) )
        ;;
      "-p")
        COMPREPLY=( $(compgen -W "project01|project02" -- $cur) )
        ;;
      *)
        ;;
    esac
  fi

  return 0
}

complete -F _grade_complete grade
