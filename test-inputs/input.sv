module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    assign sum = a ^ b ^ cin;

    assign cout = (a & b) | (b & cin) | (a & cin);
    
endmodule

module NBitFullAdder #(parameter N = 1)
(
    input logic [N-1:0] A, B,
    input logic Cin,
    output logic [N-1:0] Sum,
    output logic Cout
);

    logic [N:0] carry;
    assign carry[0] = Cin;

    genvar i;
    generate
        for (i = 0; i < N; i++) begin : adder
            FullAdder fa (
                .a(A[i]),
                .b(B[i]),
                .cin(carry[i]),
                .sum(Sum[i]),
                .cout(carry[i+1])
            );
        end
    endgenerate

    assign Cout = carry[N];

endmodule
