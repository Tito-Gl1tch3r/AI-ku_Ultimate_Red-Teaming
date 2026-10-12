%include "include/io.inc"

extern access ; pentru a verifica daca fisierul imagine exista
extern atoi
extern printf
extern exit

extern read_image ; int * read_image(char *path)
extern free_image ; void free_image(int *image)

extern get_image_width ; int get_image_width(void)
extern get_image_height ;  int get_image_height(void)

extern print_image ; void print_image(int *image, int width, int height)

section .bss
	image: resd 1
	image_width: resd 1
	image_height: resd 1

	task: resd 1

section .rodata
	xor_dec_kw_str: db "revient", 0 ; cuvantul cheie

section .text
; +-[ xor_dec_kw ]------------------------------+
; | compara caracterele de la pozitia curenta   |
; | din imagine cu cuvantul cheie               |
; +-[ primeste ]--------------------------------+
; | edi : pointer la pozitia curenta in imagine |
; | dl  : cheia folosita pentru decriptare      |
; +-[ intoarce ]--------------------------------+
; | al  : daca cuvantul cheie a fost gasit      |
; +---------------------------------------------+
xor_dec_kw:
	; salveaza vechile valori ale registrelor
	push esi
	push edi

	mov esi, xor_dec_kw_str

xor_dec_kw_cmp:
	mov dh, [edi]
	xor dh, dl

	; verifica daca a fost gasita o diferenta
	cmp dh, [esi]
	jne xor_dec_kw_diff

	inc esi
	add edi, 4
	jmp xor_dec_kw_cmp

xor_dec_kw_diff:
	; daca am ajuns la sfarsitul cuvantului cheie
	; atunci acesta a fost gasit in imagine
	cmp byte [esi], 0
	jne xor_dec_kw_end

	inc al ; marcheaza faptul ca cuvantul cheie a fost gasit

	; in acest caz nu mai este necesar sa restauram registrul `edi`
	add esp, 4
	jmp xor_dec_kw_found

xor_dec_kw_end:
	pop edi

xor_dec_kw_found:
	pop esi

	ret

; +-[ xor_dec ]------------------------------+
; | gaseste cheia folosita pentru cripatrea  |
; | mesajului in imagine si linia la care    |
; | acesta se afla                           |
; +-[ intoarce ]-----------------------------+
; | dl  : cheia folosita pentru decriptare   |
; | ecx : linia la care mesajul a fost gasit |
; +------------------------------------------+
xor_dec:
	xor al, al ; marcheaza daca cuvantul cheie a fost gasit

	xor dl, dl ; cheia pe care o incercam

xor_dec_key:
	mov edi, [image]
	xor ecx, ecx ; linia curenta din imagine

xor_dec_line:
	mov esi, edi ; salveaza inceputul liniei curente a imaginii
	             ; in eventualitatea in care gasim cuvantul cheie in ea
	xor ebx, ebx ; pixelul curent de pe linia curenta din imagine

xor_dec_pixel:
	call xor_dec_kw

	; verifica daca cuvantul cheie a fost gasit
	test al, al
	jnz xor_dec_found

	add edi, 4 ; avanseaza la urmatorul pixel

	inc ebx
	cmp ebx, [image_width]
	jne xor_dec_pixel

	inc ecx
	cmp ecx, [image_height]
	jne xor_dec_line

	add dl, 1 ; incrementeaza cheia
	          ; folosim `add` pentru ca `inc` nu actualizeaza CF
	jnc xor_dec_key

xor_dec_found:
	cmp dword [task], 1
	jne xor_dec_end

	; printeaza mesajul decriptat caracter cu caracter

	mov dh, [esi]
	xor dh, dl

	test dh, dh ; verifica daca am ajuns la terminatorul de sir
	jz xor_dec_print

	PRINT_CHAR dh

	add esi, 4
	jmp xor_dec_found

xor_dec_print:
	NEWLINE

	PRINT_DEC 1, dl
	NEWLINE

	PRINT_DEC 4, ecx
	NEWLINE

xor_dec_end:
	ret

section .rodata
	xor_enc_msg_str: db "C'est un proverbe francais.", 0

section .text
; +-[ xor_enc ]-------------------------------+
; | adauga noul mesaj in imagine si           |
; | o cripteaza folosind noua cheie calculata |
; | cu ajutorul cheii vechi                   |
; +-[ primeste ]------------------------------+
; | dl  : cheia veche pentru decriptare       |
; | ecx : linia la care se afla mesajul       |
; +-------------------------------------------+
xor_enc:
	; calculeaza noua cheie
	movzx ax, dl
	shl ax, 1 ; inmulteste cu 2
	add ax, 3
	mov dh, 5
	div dh
	sub al, 4 ; noua cheie
	mov ah, dl ; vechea cheie

	; pozitioneaza `edi` la urmatoarea linie dupa mesaj
	mov edi, [image]
	inc ecx ; treci la urmatoarea linie dupa mesajul deja existent
	imul ecx, [image_width]
	lea edi, [edi+4*ecx]

	mov esi, xor_enc_msg_str

xor_enc_copy_msg:
	; copiaza noul mesaj criptat cu vechea cheie

	mov dl, [esi]

	test dl, dl
	jz xor_enc_process

	xor dl, ah
	mov [edi], dl

	inc esi
	add edi, 4
	jmp xor_enc_copy_msg
 
xor_enc_process:
	mov [edi], ah ; adauga terminatorul de sir criptat cu vechea cheie

	; decripteaza imaginea folosind vechea cheie,
	; cripteaza imaginea folosind noua cheie

	mov edi, [image]
	xor ecx, ecx ; linia curenta din imagine

xor_enc_line:
	mov esi, edi ; inceputul liniei curente a imaginii
	xor ebx, ebx ; pixelul curent de pe linia curenta din imagine

xor_enc_pixel:
	mov dl, [edi]
	xor dl, ah
	xor dl, al
	mov [edi], dl

	add edi, 4 ; avanseaza la urmatorul pixel

	inc ebx
	cmp ebx, [image_width]
	jne xor_enc_pixel

	inc ecx
	cmp ecx, [image_height]
	jne xor_enc_line

	ret

section .rodata
	morse_enc_A: db ".-", 0
	morse_enc_B: db "-...", 0
	morse_enc_C: db "-.-.", 0
	morse_enc_D: db "-..", 0
	morse_enc_E: db ".", 0
	morse_enc_F: db "..-.", 0
	morse_enc_G: db "--.", 0
	morse_enc_H: db "....", 0
	morse_enc_I: db "..", 0
	morse_enc_J: db ".---", 0
	morse_enc_K: db "-.-", 0
	morse_enc_L: db ".-..", 0
	morse_enc_M: db "--", 0
	morse_enc_N: db "-.", 0
	morse_enc_O: db "---", 0
	morse_enc_P: db ".--.", 0
	morse_enc_Q: db "--.-", 0
	morse_enc_R: db ".-.", 0
	morse_enc_S: db "...", 0
	morse_enc_T: db "-", 0
	morse_enc_U: db "..-", 0
	morse_enc_V: db "...-", 0
	morse_enc_W: db ".--", 0
	morse_enc_X: db "-..-", 0
	morse_enc_Y: db "-.--", 0
	morse_enc_Z: db "--..", 0

	morse_enc_0: db "-----", 0
	morse_enc_1: db ".----", 0
	morse_enc_2: db "..---", 0
	morse_enc_3: db "...--", 0
	morse_enc_4: db "....-", 0
	morse_enc_5: db ".....", 0
	morse_enc_6: db "-....", 0
	morse_enc_7: db "--...", 0
	morse_enc_8: db "---..", 0
	morse_enc_9: db "----.", 0

	morse_enc_space: db "|", 0
	morse_enc_comma: db "--..--", 0


	; LUT bazat pe codificarea ASCII
	morse_enc_table_base: db ' '
	morse_enc_table: dd \
		morse_enc_space, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, \
		morse_enc_comma, 0, 0, 0, morse_enc_0, morse_enc_1, \
		morse_enc_2, morse_enc_3, morse_enc_4, morse_enc_5, \
		morse_enc_6, morse_enc_7, morse_enc_8, morse_enc_9, \
		0, 0, 0, 0, 0, 0, 0, morse_enc_A, morse_enc_B, \
		morse_enc_C, morse_enc_D, morse_enc_E, morse_enc_F, \
		morse_enc_G, morse_enc_H, morse_enc_I, morse_enc_J, \
		morse_enc_K, morse_enc_L, morse_enc_M, morse_enc_N, \
		morse_enc_O, morse_enc_P, morse_enc_Q, morse_enc_R, \
		morse_enc_S, morse_enc_T, morse_enc_U, morse_enc_V, \
		morse_enc_W, morse_enc_X, morse_enc_Y, morse_enc_Z

	morse_enc_char_delim: db ' '

section .text
; +-[ morse_enc ]-------------------------------+
; | insereaza in imagine codificarea Morse      |
; | a mesajului primit la indicele specificat   |
; | in linia de comanda                         |
; +-[ primeste ]--------------------------------+
; | esi : pointer la mesajul ce trebuie inserat |
; | edi : pointer la pozitia curenta in imagine |
; |       unde inseram mesajul                  |
; +---------------------------------------------+
morse_enc:
	xor edx, edx

morse_enc_copy_msg:
	; insereaza mesajul in reprezentare Morse in imagine

	mov dl, [esi] ; caracterul curent din mesaj

	test dl, dl
	jz morse_enc_end

	sub dl, [morse_enc_table_base] ; 
	mov eax, [morse_enc_table+4*edx] ; reprezentarea Morse a caracterului

morse_enc_copy_char:
	mov cl, [eax] ; caracterul curent din reprezentarea Morse a caracterului

	test cl, cl
	jz morse_enc_copy_char_end

	mov [edi], cl ; copiaza caracterul din reprezentarea Morse in imagine
	add edi, 4

	inc eax
	jmp morse_enc_copy_char

morse_enc_copy_char_end:
	; adauga delimitatorul de caractere in reprezentare Morse
	mov cl, [morse_enc_char_delim]
	mov [edi], cl
	add edi, 4

	inc esi
	jmp morse_enc_copy_msg

morse_enc_end:
	; inlocuieste ultimul octet din mesaj cu terminatorul de sir
	sub edi, 4
	mov byte [edi], 0

	ret

; +-[ lsb_enc ]---------------------------------+
; | insereaza in imagine codificarea LSB        |
; | a mesajului primit la indicele specificat   |
; | in linia de comanda                         |
; +-[ primeste ]--------------------------------+
; | esi : pointer la mesajul ce trebuie inserat |
; | edi : pointer la pozitia curenta in imagine |
; |       unde inseram mesajul                  |
; +---------------------------------------------+
lsb_enc:
	sub edi, 4 ; incepe de fapt de la indexul specificat -1

lsb_enc_copy_msg:
	mov dl, [esi]

	mov ecx, 8 ; parcurgem cei 8 biti ai octetului curent

lsb_enc_extract_bit:
	; extrage cel mai semnificativ bit al caracterului in `dh`
	mov dh, dl
	and dh, 0b10000000
	rol dh, 1

	mov al, [edi] ; extrage pixelul in `al`

	test dh, dh
	jnz lsb_enc_set_bit

	and al, 0b11111110 ; seteaza LSB la 0

	jmp lsb_enc_copy_bit

lsb_enc_set_bit:
	or al, 0b00000001 ; seteaza LSB la 1

lsb_enc_copy_bit:
	mov [edi], al

	add edi, 4

	rol dl, 1 ; treci la urmatorul bit din caracterul mesajului
	loop lsb_enc_extract_bit

	; am inserat un caracter in imagine

	test dl, dl ; verifica daca am ajuns la terminatorul de sir
	jz lsb_enc_end

	inc esi
	jmp lsb_enc_copy_msg

lsb_enc_end:
	ret

; +-[ lsb_dec ]---------------------------------+
; | extrage din imagine mesajul codificat LSB   |
; | ce se afla la indicele specificat in linia  |
; | de comanda, afisandu-l caracter cu caracter |
; +-[ primeste ]--------------------------------+
; | edi : pointer la pozitia curenta in imagine |
; |       de unde extragem mesajul              |
; +---------------------------------------------+
lsb_dec:
	sub edi, 4 ; incepe de fapt de la indexul specificat -1

lsb_dec_extract_byte:
	xor dh, dh

	mov ecx, 8 ; parcurgem 8 pixeli pentru a extrage un caracter

lsb_dec_extract_bit:
	mov dl, [edi]
	and dl, 0b00000001 ; extrage bitul cel mai nesemnificativ din pixel

	shl dh, 1
	or dh, dl ; adauga bitul extras la caracter

	add edi, 4

	loop lsb_dec_extract_bit

	; am extras un caracter

	test dh, dh ; verifica daca caracterul este terminatorul de sir
	jz lsb_dec_end

	PRINT_CHAR dh

	jmp lsb_dec_extract_byte

lsb_dec_end:
	NEWLINE

	ret

; +-[ blur ]------------------------+
; | aplica filtrul de blur imaginii |
; +---------------------------------+
blur:
	push ebp
	mov ebp, esp

	mov esi, [image_width] ; retinem valoarea in registru pentru ca
	                       ; e folosita in repetate randuri

	; aloca spatiu pentru memorarea valorilor liniei precedente
	; celei curente inainte ca aceasta sa fi fost procesata
	; (pentru a putea calcula noile valori ale pixelilor liniei curente
	;  inainte ca linia precedenta acesteia sa fi fost alterata)
	add esp, 2 ; cu 2 mai putin pentru ca nu avem nevoie
	           ; de primul si de ultimul pixel al liniei
	sub esp, esi

	mov edi, [image]
	add edi, 4 ; incepe de la al doilea pixel al primei linii
	mov ebx, 2 ; incepe de la 2 pentru ca nu avem nevoie
	           ; de primul si de ultimul pixel al liniei

	; initializeaza prima linie a imaginii ca linie precedenta

blur_copy_first_line:
	mov dl, [edi]
	mov [esp+ebx-2], dl

	add edi, 4 ; avanseaza la urmatorul pixel

	inc ebx
	cmp ebx, esi
	jne blur_copy_first_line

	mov ecx, 2 ; incepe de la 2 pentru ca nu facem nimic
	           ; cu prima si cu ultima linie

blur_line:
	add edi, 4 ; pentru a ajunge la primul pixel de pe urmatoarea linie
	movzx dx, byte [edi] ; valoarea nealterata a vecinului stang

	add edi, 4 ; pentru a ajunge la al doilea pixel de pe urmatoarea linie
	mov ebx, 2 ; incepe de la 2 pentru ca nu facem nimic
	           ; cu primul si cu ultimul pixel de pe linie

blur_pixel:
	movzx ax, byte [edi] ; vechea valoare a pixelului curent

	add ax, dx ; adauga vecinul stang

	; adauga vecinul de sus
	movzx dx, byte [esp+ebx-2]
	add ax, dx

	; adauga vecinul drept
	movzx dx, byte [edi+4]
	add ax, dx

	; adauga vecinul de jos
	movzx dx, byte [edi+4*esi]
	add ax, dx

	; calculeaza media aritmetica
	mov dh, 5
	div dh

	; retine valoarea nealterata a pixelului pentru linia precedenta
	movzx dx, byte [edi]
	mov [esp+ebx-2], dl

	mov [edi], al ; scrie noua valoare a pixelului

	add edi, 4 ; avanseaza la urmatorul pixel

	inc ebx
	cmp ebx, esi
	jne blur_pixel

	inc ecx
	cmp ecx, [image_height]
	jne blur_line

	leave
	ret

section .text
task1:
task2:
	call xor_dec

	cmp dword [task], 1
	je main_end

	call xor_enc

	jmp main_print_image

section .rodata
	tasks345_funcs: dd morse_enc, lsb_enc, lsb_dec

section .text
task3:
task4:
task5:
	mov eax, [ebp+12]

	mov ecx, 12

	cmp ebx, 5
	je tasks345_atoi_index

	add ecx, 4

	mov esi, [eax+12] ; mesajul ce trebuie codificat

tasks345_atoi_index:
	; indexul de unde se insereaza (pentru task-urile 3, 4)
	; sau extrage (pentru task-ul 5) mesajul
	push dword [eax+ecx]
	call atoi
	add esp, 4

	mov edi, [image]
	lea edi, [edi+4*eax] ; pozitionaza pointer-ul in imagine

	call [tasks345_funcs+4*(ebx-3)] ; apeleaza functia task-ului curent

	; pentru task-ul 5 nu afisam imaginea
	cmp ebx, 5
	je main_end

	jmp main_print_image

task6:
	call blur

	jmp main_print_image

section .rodata
	usage_str: db "Usage: %s <image> <task> [<msg> <index> | <index>]", 0x0a, 0

	tasks: dd task1, task2, task3, task4, task5, task6
	tasks_args_count: db 3, 3, 5, 5, 4, 3
	tasks_count: equ $-tasks_args_count

section .text
print_usage:
	push dword [ebx+0]
	push usage_str
	call printf
	add esp, 8

	push 1
	call exit

global main
main:
	push ebp
	mov ebp, esp

	mov ebx, [ebp+12] ; `argv`
	                  ; folosim `ebx` pentru ca este callee-saved
	                  ; (este restaurat de functia apelata, ramane nemodificat)

	; verifica daca au fost specificate argumente
	cmp dword [ebp+8], 1+2 ; numele programului + minim 2 argumente
	jb print_usage

	; verifica daca imaginea exista
	push dword 0
	push dword [ebx+4]
	call access
	add esp, 8

	test eax, eax
	jnz print_usage

	; incarca imaginea in memorie
	push dword [ebx+4]
	call read_image
	add esp, 4
	mov [image], eax

	; obtine dimensiunile imaginii
	call get_image_width
	mov [image_width], eax
	call get_image_height
	mov [image_height], eax

	; obtine numarul task-ului
	push dword [ebx+8]
	call atoi
	add esp, 4

	; verifica daca task-ul este intre 1 si numarul maxim de task-uri
	cmp eax, 1
	jb print_usage
	cmp eax, tasks_count
	ja print_usage

	; verifica daca numarul de argumente este potrivit task-ului
	mov cl, [ebp+8] ; `argc`
	cmp cl, [tasks_args_count+(eax-1)]
	jne print_usage

	mov ebx, eax
	mov [task], ebx

	jmp [tasks+4*(ebx-1)] ; sari la task-ul corespunzator

main_print_image:
	push dword [image_height]
	push dword [image_width]
	push dword [image]
	call print_image
	add esp, 12

main_end:
	; elibereaza memoria ocupata de imagine
	push dword [image]
	call free_image
	add esp, 4

	xor eax, eax
	leave
	ret
