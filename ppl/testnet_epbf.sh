#!/bin/bash

NAMESPACES=6
TMUXSN=srv6pm
IPSET=ipset
IP6TABLES=ip6tables

#######################################################################################################################################################################################################
#
#                                                                                                                                    INCAPSULA - SRH
#                                        0               1                                                                          2               3 
#                                        #################                                                                          ################# 
#                                        #      NS1      # fcf0:0000:0001:0002::1/64 -------------------- fcf0:0000:0001:0002::2/64 #      NS2      # fcf0:0000:0002:0003::1/64 ---------->
#                                        #################                                                                          ################# 
#                                        fcff:0001::1/128                                                                           fcff:0002::1/128  
#
#
#######################################################################################################################################################################################################
#
#                                         		
#                                        4      SR       5                                                                          6      SR       7 
#                                        #################                                                                          ################# 
#  <---------- fcf0:0000:0002:0003::2/64 #      NS3      # fcf0:0000:0003:0004::1/64 -------------------- fcf0:0000:0003:0004::2/64 #      NS4      # fcf0:0000:0004:0005::1/64 ---------->
#                                        #################                                                                          ################# 
#                                        fcff:0003::1/128                                                                           fcff:0004::1/128  
#
#
#######################################################################################################################################################################################################
#
#                                         SCAPSULA - SRH
#                                        8               9                                                                          10             11 
#                                        #################                                                                          ################# 
#  <---------- fcf0:0000:0004:0005::2/64 #      NS5      # fcf0:0000:0005:0006::1/64 -------------------- fcf0:0000:0005:0006::2/64 #      NS6      # 
#                                        #################                                                                          ################# 
#                                        fcff:0005::1/128                                                                           fcff:0006::1/128  
#
#
########################################################################################################################################################################################################



if [ $# -eq 0 ]; then
	echo "No arguments supplied"
else
	NAMESPACES=$1
fi



# $1 = num of interfaces to clean
cleanup(){

	for i in $(seq 1 $1)
	do
	   	echo "cleanup NS$i"
		#udo ip netns del NS$i 2> /dev/null
		sudo ip netns del NS$i
	done
	sudo ip netns del CTRL

	echo "Killing wireshark.."
	sudo pkill wireshark
	
	echo "Cleanup done\n"
}

create_controller(){
	echo "Setting-up CTRL namespace"

	# ADDING THE CONTROLLER AND RELATIVE INTERFACES
	echo "\nSetting-up The controller"
	
	echo "Creating the Controller Namespace"
	sudo ip netns add CTRL
	
	
	echo "Creating the virtual interfaces veth-c{0:2} connected respectively to br-veth-c{0:2}"
	sudo ip link add veth-c0 type veth peer name br-veth-c0
	sudo ip link add veth-c1 type veth peer name br-veth-c1
	sudo ip link add veth-c2 type veth peer name br-veth-c2
		
	echo "Adding virtual interfaces veth-c{0:2} to CTRL, NS2 and NS(N-1) respectively"
	sudo ip link set veth-c0 netns CTRL
	sudo ip link set veth-c1 netns NS2
	sudo ip link set veth-c2 netns NS$(($NAMESPACES - 1))
	
	#NB: attached to the "real" machine. Should I move them?
	echo "Set up controller bridge"
	sudo ip link add name br-ctrl type bridge
	sudo ip link set br-ctrl up
	
	#NB: attached to the "real" machine. Should I move them?
	echo "Enabling bridge interfaces"
	sudo ip link set br-veth-c0 up
	sudo ip link set br-veth-c1 up
	sudo ip link set br-veth-c2 up

	sudo ip netns exec CTRL ip link set dev br-veth-c0 up
	sudo ip netns exec CTRL ip link set dev br-veth-c1 up
	sudo ip netns exec CTRL ip link set dev br-veth-c2 up

		
	echo "Connecting br-veth-c{0:2} interfaces to the bridge"
	sudo ip link set br-veth-c0 master br-ctrl
	sudo ip link set br-veth-c1 master br-ctrl
	sudo ip link set br-veth-c2 master br-ctrl
		
		
	echo "Enabling interfaces veth-c{0:2}"
	sudo ip netns exec CTRL ip link set dev veth-c0 up
	sudo ip netns exec NS2 ip link set dev veth-c1 up
	sudo ip netns exec NS$(($NAMESPACES - 1)) ip link set dev veth-c2 up
		
		
	echo "Adding addresses and routes to CTRL net"
	sudo ip netns exec CTRL ip addr add 10.1.1.100/24 dev veth-c0
	sudo ip netns exec NS2 ip addr add 10.1.1.1/24 dev veth-c1
	sudo ip netns exec NS$(($NAMESPACES - 1)) ip addr add 10.1.1.2/24 dev veth-c2
	
		
	echo "Adding loopback interface to CTRL"
	sudo ip netns exec CTRL ip link set dev lo up
		
	echo "Adding loopback address to CTRL"
	sudo ip netns exec CTRL ip addr add 127.0.0.1 dev lo
	
}


create_first_NS(){
	echo "Setting-up NS1"
	
	echo "Creating the virtual interface connected to veth2"
	sudo ip link add veth1 type veth peer name veth2
	
	echo "Creating the NS1"
	sudo ip netns add NS1
	
	echo "Adding virtual interface to NS1"
	sudo ip link set veth1 netns NS1
	
	echo "Enabling interfaces for NS1"
	sudo ip netns exec NS1 ip link set dev veth1 up
	
	
	echo "Adding addresses and routes to NS1"
	sudo ip netns exec NS1 ip -6 addr add fcf0:0000:0001:0002::1/64 dev veth1
		
	#echo "Adding next host route"
	#sudo ip netns exec NS1 ip -6 addr add fc00::$(($1 + 1))0 dev $RIGHT_IFACE #scope link
	
	echo "Adding default route"
	sudo ip netns exec NS1 ip -6 route add default via fcf0:0000:0001:0002::2 
	
	
	
	echo "Adding loopback interface to NS1"
	sudo ip netns exec NS1 ip link set dev lo up
	
	echo "Adding loopback address to NS1"
	sudo ip netns exec NS1 ip -6 addr add fcff:0001::1 dev lo

	echo "Setting-up NS1 done\n"
}

# $1 = namespace number
create_encap_NS(){
	echo "Setting-up ENCAP - NS$1" 
	NSX=NS$1
	
	PREV_IFACE_N=$(((($1 - 1) * 2) - 1))
	NEXT_IFACE_N=$(($1 * 2))
	
	LEFT_IFACE_N=$((($1 - 1) * 2))
	RIGHT_IFACE_N=$((($1 * 2) - 1))
	
	LEFT_IFACE=veth$LEFT_IFACE_N
	RIGHT_IFACE=veth$RIGHT_IFACE_N
	
	NEXT_IFACE=veth$NEXT_IFACE_N

	EPBF_BRIDGE=br$1
	EPBF_IGR_IFACE=veth${RIGHT_IFACE_N}-igr
	EPBF_EGR_IFACE=veth${RIGHT_IFACE_N}-egr

	echo "Creating the virtual interfaces: $RIGHT_IFACE and $NEXT_IFACE"
	sudo ip link add $RIGHT_IFACE type veth peer name $NEXT_IFACE

	echo "Creating the virtual interfaces: $EPBF_IGR_IFACE and $EPBF_EGR_IFACE"
	sudo ip link add $EPBF_IGR_IFACE type veth peer name $EPBF_EGR_IFACE
    
	echo "Creating the $NSX"
	sudo ip netns add $NSX
	
	echo "Adding virtual interface to $NSX"
	sudo ip link set $LEFT_IFACE netns $NSX
	sudo ip link set $RIGHT_IFACE netns $NSX

    echo "Adding virtual interface EPBF to $NSX"
	sudo ip link set $EPBF_IGR_IFACE netns $NSX
	sudo ip link set $EPBF_EGR_IFACE netns $NSX

    echo "Adding Bridge for EPBF to $NSX"
    sudo ip netns exec $NSX ip link add name $EPBF_BRIDGE type bridge

	echo "Enabling interfaces for $NSX"
	sudo ip netns exec $NSX ip link set dev $EPBF_BRIDGE up
	sudo ip netns exec $NSX ip link set dev $LEFT_IFACE up
	sudo ip netns exec $NSX ip link set dev $RIGHT_IFACE up
	sudo ip netns exec $NSX ip link set dev $EPBF_IGR_IFACE up
	sudo ip netns exec $NSX ip link set dev $EPBF_EGR_IFACE up

    echo "Connect interfaces to Bridge"
    sudo ip netns exec $NSX ip link set $EPBF_EGR_IFACE master $EPBF_BRIDGE
	sudo ip netns exec $NSX ip link set $RIGHT_IFACE master $EPBF_BRIDGE

	
	echo "Adding addresses and routes to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcf0:0000:000$(($1 - 1)):000$(($1))::02/64 dev $LEFT_IFACE #scope link
	sudo ip netns exec $NSX ip -6 addr add fcf0:0000:000$(($1)):000$(($1 + 1))::01/64 dev $EPBF_IGR_IFACE #per epbf
    
	echo "Adding loopback interface to $NSX"
	sudo ip netns exec $NSX ip link set dev lo up
	
	echo "Adding loopback address to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcff:000$(($1))::1 dev lo
	
	echo "Enabling forwarding"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.forwarding=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv4.conf.all.forwarding=1 > /dev/null
	
	echo "Enabling SRV6"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.lo.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$LEFT_IFACE.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$RIGHT_IFACE.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$EPBF_IGR_IFACE.seg6_enabled=1 > /dev/null
	
	echo "Adding next host route"
	sudo ip netns exec $NSX ip -6 route add fcff:000$(($1 + 1))::/32 via fcf0:0000:000$(($1)):000$(($1 + 1))::02 #dev $RIGHT_IFACE via fb$(($1))0::02
	
	echo "Adding previous host route"
	sudo ip netns exec $NSX ip -6 route add fcff:000$(($1 - 1))::/32 via fcf0:0000:000$(($1 - 1)):000$(($1))::01 #dev $LEFT_IFACE via fb$(($1 - 1))0::01
	
	echo "Setting-up $NSX done\n"
}

# $1 = namespace number
create_NS(){
	echo "Setting-up NS$1"
	NSX=NS$1
	
	PREV_IFACE_N=$(((($1 - 1) * 2) - 1))
	NEXT_IFACE_N=$(($1 * 2))
	
	LEFT_IFACE_N=$((($1 - 1) * 2))
	RIGHT_IFACE_N=$((($1 * 2) - 1))
	
	LEFT_IFACE=veth$LEFT_IFACE_N
	RIGHT_IFACE=veth$RIGHT_IFACE_N
	
	NEXT_IFACE=veth$NEXT_IFACE_N
	
	echo "Creating the virtual interfaces: $RIGHT_IFACE and $NEXT_IFACE"
	sudo ip link add $RIGHT_IFACE type veth peer name $NEXT_IFACE
	
	echo "Creating the $NSX"
	sudo ip netns add $NSX
	
	echo "Adding virtual interface to $NSX"
	sudo ip link set $LEFT_IFACE netns $NSX
	sudo ip link set $RIGHT_IFACE netns $NSX
	
	echo "Enabling interfaces for $NSX"
	sudo ip netns exec $NSX ip link set $LEFT_IFACE up
	sudo ip netns exec $NSX ip link set $RIGHT_IFACE up
	
	
	echo "Adding addresses and routes to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcf0:0000:000$(($1 - 1)):000$(($1))::02/64 dev $LEFT_IFACE #scope link
	sudo ip netns exec $NSX ip -6 addr add fcf0:0000:000$(($1)):000$(($1 + 1))::01/64 dev $RIGHT_IFACE #scope link
	#sudo ip netns exec $NSX ip -6 route add fb$(($1 - 1))0::$NEXT_IFACE_N$RIGHT_IFACE_N dev $RIGHT_IFACE #scope link
	#sudo ip netns exec $NSX ip -6 route add fb$(($1 + 1))0::$PREV_IFACE_N$LEFT_IFACE_N dev $LEFT_IFACE #scope link
	
	echo "Adding loopback interface to $NSX"
	sudo ip netns exec $NSX ip link set dev lo up
	
	echo "Adding loopback address to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcff:000$(($1))::1 dev lo
	
	echo "Enabling forwarding"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.forwarding=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv4.conf.all.forwarding=1 > /dev/null
	
	echo "Enabling SRV6"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.lo.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$LEFT_IFACE.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$RIGHT_IFACE.seg6_enabled=1 > /dev/null
	
	echo "Adding next host route"
	sudo ip netns exec $NSX ip -6 route add fcff:000$(($1 + 1))::/32 via fcf0:0000:000$(($1)):000$(($1 + 1))::02 #dev $RIGHT_IFACE via fb$(($1))0::02
	
	echo "Adding previous host route"
	sudo ip netns exec $NSX ip -6 route add fcff:000$(($1 - 1))::/32 via fcf0:0000:000$(($1 - 1)):000$(($1))::01 #dev $LEFT_IFACE via fb$(($1 - 1))0::01
	
	echo "Setting-up $NSX done\n"
}


# $1 = namespace number
create_last_NS(){
	echo "Setting-up NS$1"
	NSX=NS$1
	
	PREV_IFACE_N=$(((($1 - 1) * 2) - 1))
	
	LEFT_IFACE_N=$((($1 - 1) * 2))
	
	LEFT_IFACE=veth$LEFT_IFACE_N
	
	
	echo "Creating the $NSX"
	sudo ip netns add $NSX
	
	echo "Adding virtual interface to $NSX"
	sudo ip link set $LEFT_IFACE netns $NSX
	
	echo "Enabling interfaces for $NSX"
	sudo ip netns exec $NSX ip link set $LEFT_IFACE up
	
	
	echo "Adding addresses and routes to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcf0:0000:000$(($1 - 1)):000$(($1))::02/64 dev $LEFT_IFACE #scope link
	
	#echo "Adding previous host route"
	#sudo ip netns exec $NSX ip -6 addr add fc00::$(($1 - 1))0 dev $LEFT_IFACE #scope link
	
	##echo "Adding first host route"
	##sudo ip netns exec $NSX ip -6 addr add fc00::10 dev $LEFT_IFACE #scope link
	echo "Adding default route"
	sudo ip netns exec $NSX ip -6 route add default via fcf0:0000:000$(($1 - 1)):000$(($1))::01
	
	
	echo "Adding loopback interface to $NSX"
	sudo ip netns exec $NSX ip link set dev lo up
	
	echo "Adding loopback address to $NSX"
	sudo ip netns exec $NSX ip -6 addr add fcff:000$(($1))::1 dev lo
	
	
	echo "Enabling SRV6 JUST FOR TESTING"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.lo.seg6_enabled=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv6.conf.$LEFT_IFACE.seg6_enabled=1 > /dev/null
	
	echo "Enabling forwarding JUST FOR TESTING"
	sudo ip netns exec $NSX sysctl net.ipv6.conf.all.forwarding=1 > /dev/null
	sudo ip netns exec $NSX sysctl net.ipv4.conf.all.forwarding=1 > /dev/null
	
	echo "Setting-up $NSX done\n"
}


create_tmpfile_namespace(){
	TMPFILE=$(mktemp)

	# Add stuff to the temporary file
	echo "source ~/.bashrc" > $TMPFILE
	echo "PS1=\"\[$(tput bold)\e[92m\]\u@\[\e[m\]\[$(tput bold)\e[31;43m\]NS$1\[\e[m\]\[$(tput bold)\e[94m\]:\w\[\e[m\]\$ \"" >> $TMPFILE
	echo "rm -f $TMPFILE" >> $TMPFILE
	
	echo $TMPFILE
}




create_tmux_space(){

read -r -d '' ebpf_env <<-'EOF'
	# Everything that is private to the bash process that will be launch

	# mount the bpf filesystem.
	# Note: childs of the launching (parent) bash can access this instance
	# of the bpf filesystem. If you need to get access to the bpf filesystem
	# (where maps are available), you need to use nsenter with -m and -t
	# that points to the pid of the parent process (launching bash).
	mount -t bpf bpf /sys/fs/bpf/

	# Load the ebpf program on the veth1 interface
	#./xdp_loader --dev veth1 --force

	export PYTHONPATH="${PYTHONPATH}:./grpc-services/protos/gen-py:./twamp:../xdp_experiments/srv6-pfplm/"
	
	/bin/bash
EOF

    tmux new-session -d -s $TMUXSN -n CTRL ip netns exec CTRL bash -c "${ebpf_env}"
    for i in $(seq 1 $1)
    do
        tmux new-window -t $TMUXSN -n NS$i ip netns exec NS$i bash -c "${ebpf_env}"
    done
        
    #load python venv 
    tmux send-keys -t CTRL "source venv/bin/activate" C-m
    tmux send-keys -t NS2 "source venv/bin/activate" C-m
    tmux send-keys -t NS$(($NAMESPACES-1)) "source venv/bin/activate" C-m 
    
    
    
    tmux send-keys -t NS2 "python ./twamp/twamp_demon.py 10.1.1.1 50052 2" C-m
    tmux send-keys -t NS$(($NAMESPACES-1)) "python ./twamp/twamp_demon.py 10.1.1.2 50052 5" C-m
    tmux send-keys -t CTRL "python ./twamp/twamp_test.py" C-m

	
    
    #start iperf session
    tmux send-keys -t NS$(($NAMESPACES)) "iperf3 -s -B fcff:$(($NAMESPACES))::1" C-m
    sleep 1
    tmux send-keys -t NS1 "iperf3 -6 -B fcff:1::1 -M 1000 -c fcff:$(($NAMESPACES))::1 -b 10M -t 3000" C-m
    
    
    
    #tmux send-keys -t NS1 source .venv/bin/

        

    tmux select-window -t CTRL
    tmux set-option -g mouse on
    tmux attach -t $TMUXSN    
}




cleanup $NAMESPACES

# Kill tmux previous session
tmux kill-session -t $TMUXSN 2>/dev/null




create_first_NS

create_encap_NS 2

for i in $(seq 3 $(($NAMESPACES - 1 )))
do
	create_NS $i
done

#create_decap_NS $NAMESPACES-1

create_last_NS $NAMESPACES

create_controller

# Creating segments
SEGS_1=""
SEGS_2=""
SEGS_CONTROLLO=""
for i in $(seq 3 $(($NAMESPACES - 1 )))
do
	SEGS_1="${SEGS_1}fcff:000$(($i))::1"
	SEGS_2="${SEGS_2}fcff:000$(($NAMESPACES + 1 - $i))::1"
	
	if [ "$i" -lt $(($NAMESPACES - 1 )) ]; then
		SEGS_1="${SEGS_1},"
		SEGS_2="${SEGS_2},"
		SEGS_CONTROLLO="${SEGS_CONTROLLO}fcff:000$(($i))::1"
	fi

	if [ "$i" -lt $(($NAMESPACES - 2 )) ]; then
		SEGS_CONTROLLO="${SEGS_CONTROLLO},"
	fi
	
done


echo "Creating SRv6 routes"
#SRV6 routes
sudo ip netns exec NS2 ip -6 route add fcff:000$(($NAMESPACES))::/32 encap seg6 mode encap segs ${SEGS_1} via fcf0:0000:0002:0003::2
sudo ip netns exec NS2 ip -6 route add fcf0:0000:000$(($NAMESPACES - 1)):000$(($NAMESPACES))::2 encap seg6 mode encap segs ${SEGS_1} via fcf0:0000:0002:0003::2

#Regola per comunicare direttamente col NAMESPACE CHE RISPONDE AI PACCHETTI
sudo ip netns exec NS2 ip -6 route add fcff:000$(($NAMESPACES-1))::/32 encap seg6 mode encap segs ${SEGS_CONTROLLO} via fcf0:0000:0002:0003::2

#SRV6 return routes
sudo ip netns exec NS$(($NAMESPACES - 1)) ip -6 route add fcff:0001::/32 encap seg6 mode encap segs ${SEGS_2} via fcf0:0000:000$(($NAMESPACES - 2)):000$(($NAMESPACES - 1))::1
sudo ip netns exec NS$(($NAMESPACES - 1)) ip -6 route add fcf0:0000:0001:0002::1 encap seg6 mode encap segs ${SEGS_2} via fcf0:0000:000$(($NAMESPACES - 2)):000$(($NAMESPACES - 1))::1






######################################### IPSET COUNTERS
echo "Adding counter to NS2"
# IPSET simple configuration
# Red hashtable
ip netns exec NS2 $IPSET -N red-ht-out sr6hash counters skbinfo
ip netns exec NS2 $IPSET -A red-ht-out ${SEGS_1} skbmark 0x01

ip netns exec NS2 $IPSET -N blue-ht-out sr6hash counters skbinfo
ip netns exec NS2 $IPSET -A blue-ht-out ${SEGS_1} skbmark 0x02

# Add or remove another rule for the blue sub-chain. This avoids to lose
# traffic while a new color is going to be applied.
ip netns exec NS2 $IP6TABLES -N red-out -t mangle
ip netns exec NS2 $IP6TABLES -N blue-out -t mangle

# XXX: test for setting any tos packet to a given value
# ip netns exec NS2 $IP6TABLES -A POSTROUTING -t mangle -j TOS --set-tos 0x02

ip netns exec NS2 $IP6TABLES -A POSTROUTING -t mangle -m rt --rt-type 4 -j red-out
ip netns exec NS2 $IP6TABLES -I POSTROUTING 1 -t mangle -m rt --rt-type 4 -j blue-out

# just to add or remove red rule for instance (rimane la rossa in fallback):
# ip6tables -D POSTROUTING -t mangle -m rt --rt-type 4 -j blue-out
# ip6tables -I POSTROUTING 1 -t mangle -m rt --rt-type 4 -j blue-out

# For red coloring
ip netns exec NS2 $IP6TABLES -A red-out -t mangle \
	-m set --match-set red-ht-out dst -j SET --map-set red-ht-out dst --map-mark

ip netns exec NS2 $IP6TABLES -A red-out -t mangle \
	-m mark --mark 0x1 -j TOS --set-tos 0x01

ip netns exec NS2 $IP6TABLES -A red-out -t mangle -j ACCEPT

# For blue coloring
ip netns exec NS2 $IP6TABLES -A blue-out -t mangle \
	-m set --match-set blue-ht-out dst -j SET --map-set blue-ht-out dst --map-mark

ip netns exec NS2 $IP6TABLES -A blue-out -t mangle \
	-m mark --mark 0x2 -j TOS --set-tos 0x02

ip netns exec NS2 $IP6TABLES -A blue-out -t mangle -j ACCEPT


# IPSET simple configuration
# Red hashtable
ip netns exec NS2 $IPSET -N red-ht-in sr6hash counters
ip netns exec NS2 $IPSET -A red-ht-in ${SEGS_2}

ip netns exec NS2 $IPSET -N blue-ht-in sr6hash counters
ip netns exec NS2 $IPSET -A blue-ht-in ${SEGS_2}

# Add or remove another rule for the blue sub-chain. This avoids to lose
# traffic while a new color is going to be applied.
ip netns exec NS2 $IP6TABLES -N red-in -t mangle
ip netns exec NS2 $IP6TABLES -N blue-in -t mangle


ip netns exec NS2 $IP6TABLES -A PREROUTING -t mangle \
	-m rt --rt-type 4 -m tos --tos 0x01  -j red-in

ip netns exec NS2 $IP6TABLES -A PREROUTING -t mangle \
	-m rt --rt-type 4 -m tos --tos 0x02 -j blue-in

# For red coloring
ip netns exec NS2 $IP6TABLES -A red-in -t mangle \
	-m set --match-set red-ht-in dst -j TOS --set-tos 0x00

# For blue coloring
ip netns exec NS2 $IP6TABLES -A blue-in -t mangle \
	-m set --match-set blue-ht-in dst -j TOS --set-tos 0x00

# This sends packets directly to nfqueue
#ip netns exec NS2 ip6tables -A INPUT -d fcff:2::1/128 -p udp --dport 1215 --sport 1216 -j NFQUEUE --queue-num 1





echo "Adding counter to NS$(($NAMESPACES - 1))"
# IPSET simple configuration
# Red hashtable
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -N red-ht-out sr6hash counters skbinfo
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -A red-ht-out ${SEGS_2} skbmark 0x01

ip netns exec NS$(($NAMESPACES - 1)) $IPSET -N blue-ht-out sr6hash counters skbinfo
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -A blue-ht-out ${SEGS_2} skbmark 0x02

# Add or remove another rule for the blue sub-chain. This avoids to lose
# traffic while a new color is going to be applied.
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -N red-out -t mangle
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -N blue-out -t mangle

# XXX: test for setting any tos packet to a given value
# ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A POSTROUTING -t mangle -j TOS --set-tos 0x02

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A POSTROUTING -t mangle \
	-m rt --rt-type 4 -j red-out

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -I POSTROUTING 1 -t mangle \
	-m rt --rt-type 4 -j blue-out

# just to add or remove red rule for instance:
# ip6table-legacy -D POSTROUTING -t mangle -j blue-out
# ip6table-legacy -I POSTROUTING 1 -t mangle -m rt --rt-type 4 -j blue-out

# For red coloring
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A red-out -t mangle \
	-m set --match-set red-ht-out dst -j SET --map-set red-ht-out dst --map-mark

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A red-out -t mangle \
	-m mark --mark 0x1 -j TOS --set-tos 0x01

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A red-out -t mangle -j ACCEPT

# For blue coloring
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A blue-out -t mangle \
	-m set --match-set blue-ht-out dst -j SET --map-set blue-ht-out dst --map-mark

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A blue-out -t mangle \
	-m mark --mark 0x2 -j TOS --set-tos 0x02

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A blue-out -t mangle -j ACCEPT


# IPSET simple configuration
# Red hashtable
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -N red-ht-in sr6hash counters
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -A red-ht-in ${SEGS_1}

ip netns exec NS$(($NAMESPACES - 1)) $IPSET -N blue-ht-in sr6hash counters
ip netns exec NS$(($NAMESPACES - 1)) $IPSET -A blue-ht-in ${SEGS_1}

# Add or remove another rule for the blue sub-chain. This avoids to lose
# traffic while a new color is going to be applied.
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -N red-in -t mangle
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -N blue-in -t mangle


ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A PREROUTING -t mangle \
	-m rt --rt-type 4 -m tos --tos 0x01  -j red-in

ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A PREROUTING -t mangle \
	-m rt --rt-type 4 -m tos --tos 0x02 -j blue-in

# For red coloring
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A red-in -t mangle \
	-m set --match-set red-ht-in dst -j TOS --set-tos 0x00

# For blue coloring
ip netns exec NS$(($NAMESPACES - 1)) $IP6TABLES -A blue-in -t mangle \
	-m set --match-set blue-ht-in dst -j TOS --set-tos 0x00

# This sends packets directly to nfqueue
#ip netns exec NS$(($NAMESPACES - 1)) ip6tables -A INPUT -d fcff:$(($NAMESPACES - 1))::1/128 -p udp --dport 1205 --sport 1206 -j NFQUEUE --queue-num 1



echo "Adding Punt to NS2"

sudo ip link add veth-punt1 type veth peer name dum-punt1
sudo ip link set veth-punt1 netns NS2
sudo ip link set dum-punt1 netns NS2
sudo ip netns exec NS2 ip link set dev veth-punt1 up
sudo ip netns exec NS2 ip link set dev dum-punt1 up
sudo ip netns exec NS2 ip -6 route add fcff:2::100 encap seg6local action End.OP oif veth-punt1 dev veth-punt1

echo "Adding Punt to NS$(($NAMESPACES - 1))"
sudo ip link add veth-punt2 type veth peer name dum-punt2
sudo ip link set veth-punt2 netns NS$(($NAMESPACES - 1))
sudo ip link set dum-punt2 netns NS$(($NAMESPACES - 1))
sudo ip netns exec NS$(($NAMESPACES - 1)) ip link set dev veth-punt2 up
sudo ip netns exec NS$(($NAMESPACES - 1)) ip link set dev dum-punt2 up
sudo ip netns exec NS$(($NAMESPACES - 1)) ip -6 route add fcff:$(($NAMESPACES - 1))::100 encap seg6local action End.OP oif veth-punt2 dev veth-punt2



######################################

echo "Starting terminals..."
sleep 2

create_tmux_space $NAMESPACES







#SRV6... incapsulata
#sudo ip -6 route add fc00::30 encap seg6 mode encap segs fb00::20,fb00::30 dev veth1

#SRV6... inline
#sudo ip -6 route add fc00::30 encap seg6 mode inline segs fb00::20,fb00::30 dev veth1





















