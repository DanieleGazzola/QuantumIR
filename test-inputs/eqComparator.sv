module eqComparator (
    input logic a0, a1, b0, b1,
    output logic eq
);
    assign eq = ~(a1 ^ b1) & ~(a0 ^ b0); // Se entrambi i bit sono uguali, eq = 1
endmodule
