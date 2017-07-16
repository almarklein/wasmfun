# Version of find_nth_prime() in Julia, for comparing speeds.
# This takes about 2.3 s on both Julia version 0.5.2 and 0.6.0.
#
# Please let me know if this can be optimized (in terms of Julia tricks,
# not the algorithm itself).

function find_nth_prime(i_max::Int64)
    n = 0
    i = -1
    
    while n < i_max
        i = i + 1
        
        if i <= 1
            continue  # nope
        elseif i == 2
            n = n + 1
        else
            gotit = 1
            for j in 2:(div(i, 2) + 1)  # note the integer division, // is rational!
                if i % j == 0
                    gotit = 0
                    break
                end
            end
            if gotit == 1
                n = n + 1
            end
        end
    end
    return i
end

# Let the JIT warm up
find_nth_prime(11)

tic()
i = find_nth_prime(10001)
toc()

println(i)
