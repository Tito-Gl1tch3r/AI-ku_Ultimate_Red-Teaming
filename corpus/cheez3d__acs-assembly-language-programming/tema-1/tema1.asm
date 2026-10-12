%include "includes/io.inc"

; offset-urile membrilor in structura nod
%define data_offset 0
%define left_offset 4
%define right_offset 8

; functie macro pentru accesarea unui membru
; dintr-un pointer la o structura nod
; %1: registrul in care sa se stocheze membrul
; %2: registrul/adresa in/la care este pointerul la structura nod
; %3: membrul ce se doreste a fi accesat, specificat prin offset
%macro get_member 3
	mov %1, %2
	mov %1, [%1+%3]
%endmacro

extern getAST
extern freeAST

section .bss
	root: resd 1 ; radacina arborelui

section .rodata
	; tabela de salturi folosita pentru a sari la operatia potrivita
	; (se foloseste de faptul ca in ASCII caracterele
	;  '+', '-', '*' si '/' sunt foarte apropiate
	;  unul fata de celalalt, aflandu-se la maxim un caracter distanta)
	ops: dd mul_op, add_op, 0, sub_op, 0, div_op

section .text
; functie pentru a transforma un sir de caractere
; ce contine un numar intr-un numar;
; primeste un pointer la sir in `esi`;
; intoarce numarul in `eax`;
atoi:
	xor eax, eax

atoi_convert:
	movzx ebx, byte [esi]
	test ebx, ebx
	jz atoi_end

	imul eax, 10

	sub ebx, '0'
	add eax, ebx

	inc esi
	jmp atoi_convert

atoi_end:
	test cl, cl ; daca sirul are minus in fata
	jnz atoi_positive_number
	neg eax

atoi_positive_number:
	ret

; cele patru operatii aritmetie;
; primesc numerele in `eax` si `ebx`;
; intorc rezultatul operatiei in `eax`;

add_op:
	add eax, ebx
	ret

sub_op:
	sub eax, ebx
	ret

mul_op:
	imul eax, ebx
	ret

div_op:
	cdq
	idiv ebx
	ret

; functia de evaluare a expresiei stocate intr-un arbore;
; primeste un pointer la radacina pe stiva;
; intoarce rezultatul expresiei in `eax`;
eval:
	; verifica daca nodul este frunza
	; si deci daca contine un numar
	get_member ecx, [esp+4], left_offset
	get_member edx, [esp+4], right_offset
	cmp ecx, edx
	jne eval_continue

	get_member esi, [esp+4], data_offset
	mov cl, [esi]
	sub cl, '-'
	jnz eval_positive_number
	inc esi

eval_positive_number:
	xor edx, edx
	call atoi
	jmp eval_end

eval_continue:
	; evalueaza expresia fiului stang
	push ecx
	call eval
	mov [esp], eax

	; evalueaza expresia fiului drept	
	get_member edx, [esp+8], right_offset
	push edx
	call eval
	mov [esp], eax

	; determina la ce operatie trebuie sa sarim
	; in functie de caracterul din nod
	get_member esi, [esp+12], data_offset
	mov esi, [esi]
	sub esi, '*'

	pop ebx
	pop eax
	call [ops+4*esi]

eval_end:
	ret

global main
main:
	push ebp
	mov ebp, esp
	
	; construieste arborele
	call getAST
	mov [root], eax

	; evalueaza expresia continuta de arbore
	push eax
	call eval
	add esp, 4

	; afiseaza rezultatul
	PRINT_DEC 4, eax
	NEWLINE

	; elibereaza memoria ocupata de arbore
	push dword [root]
	call freeAST

	xor eax, eax
	leave
	ret
