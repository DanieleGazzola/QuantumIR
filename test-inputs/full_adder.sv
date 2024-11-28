module FullAdder(
    input  logic a, b, cin,
    output logic sum, cout
);

    assign  sum = a ^ b ^ cin;                       // Somma dei bit
    assign  cout = (a & b) | (b & cin) | (a & cin);  // Calcolo del carry  
        
endmodule