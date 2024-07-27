module FullAdder(input logic a, b, cin,
                 output logic sum, cout);

    // Function to calculate sum
    function logic calc_sum(input logic a, b, cin);
        logic xor_1;
        xor_1 = a ^ b;
        return xor_1 ^ cin;
    endfunction

    // Function to calculate carry out
    function logic calc_cout(input logic a, b, cin);
        logic xor_1, and_1, and_2;
        xor_1 = a ^ b;
        and_1 = a & b;
        and_2 = xor_1 & cin;
        return and_1 | and_2;
    endfunction

    // Use the functions to assign the outputs
    assign sum = calc_sum(a, b, cin);
    assign cout = calc_cout(a, b, cin);
    
endmodule