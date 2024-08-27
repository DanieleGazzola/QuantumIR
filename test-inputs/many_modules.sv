// Modulo 1: Sommatore
module adder (
    input a,  // Primo bit
    input b,  // Secondo bit
    output sum,  // Risultato della somma
    output carry_out  // Carry out della somma
);
    assign sum = a ^ b;  // Somma bit a bit (XOR)
    assign carry_out = a & b;  // Carry bit (AND)
endmodule

// Modulo 2: Moltiplicatore
module multiplier (
    input x,  // Primo bit
    input y,  // Secondo bit
    output product  // Risultato della moltiplicazione
);
    assign product = x & y;  // Moltiplicazione bit a bit (AND)
endmodule

// Modulo 3: Modulo principale
module top_module (
    input a,  // Primo bit per la somma
    input b,  // Secondo bit per la somma
    input c,  // Bit per la moltiplicazione
    output result,  // Risultato finale
    output carry_out  // Carry out della somma
);
    wire sum;       // Wire per collegare il risultato della somma
    wire product;   // Wire per collegare il risultato della moltiplicazione

    // Instanziazione del modulo sommatore
    adder u1 (
        .a(a),
        .b(b),
        .sum(sum),
        .carry_out(carry_out)
    );

    // Instanziazione del modulo moltiplicatore
    multiplier u2 (
        .x(sum),
        .y(c),
        .product(result)
    );

endmodule
