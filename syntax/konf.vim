" Vim syntax file
" Language: Konf
" Maintainer: Justaus3r
" Lastest Revision: 12 Mar 2023

if exists("b:current_syntax")
    finish
endif

" TODO: match custom Section names

syn keyword KonfBoolean True False
syn keyword konfSection START END 
syn keyword SectionName play_history 
syn match SectionName /player_\d\+/
syn match konfSpecial /\v(\-\>|\@meta|\@META|\<\-|\:\:|\:|\<)/
syn match konfComment /\v(#|").*/
syn match konfNumber /\d\+/

:let b:current_syntax = "konf"

hi def link KonfSection Keyword
hi def link SectionName Identifier
hi def link KonfSpecial SpecialChar
hi def link KonfComment Comment
hi def link konfNumber  Number
hi def link KonfBoolean Boolean


