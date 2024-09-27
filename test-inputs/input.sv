module combinational_example(
    input logic [3:0] a,  
    input logic [3:0] b,  
    output logic [3:0] sum,
    output logic [4:0] out
    );

    // Logica combinatoria per somma
    always_comb begin
        sum = a ^ b; // Somma combinatoria
        out = a & b;
    end

endmodule
